"""
chests.py — Сундуки (Chests) import endpoint.

POST /api/v1/chests/import — принимает батч сундуков от бота, изолирует данные по
тенанту [kingdom, clan, user_id] (ChestCollector), применяет alias-словари сборщика
к имени игрока и типу сундука перед записью, и атомарно списывает кредиты за батч
(только если в батче есть хотя бы одна новая запись — повторная отправка уже
сохранённого батча бесплатна, это и есть смысл идемпотентности).

Auth: hwid в payload → User (как /use_credit), НЕ Bearer ADMIN_TOKEN — вызывается
рядовыми платящими пользователями бота, а не админ-скриптами.
"""
import secrets
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Chest, ChestCollector, ChestTypeAlias, Hunt, PlayerAlias, Transaction, User

router = APIRouter(prefix="/api/v1/chests", tags=["chests"])

# Стоимость одной отправки батча (флэт, не за штуку) — отдельная константа от
# CREDIT_COST в main.py, чтобы не создавать циклический импорт main<->chests.
CHEST_IMPORT_COST = 10


class ChestItemIn(BaseModel):
    chest_type: str
    sender: str
    timestamp: str


class ChestImportPayload(BaseModel):
    hwid: str
    kingdom: str
    clan: str
    timestamp: str
    items: List[ChestItemIn]


async def _get_or_create_collector(kingdom: str, clan: str, user_id: int,
                                   db: AsyncSession) -> ChestCollector:
    existing = (await db.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == kingdom,
            ChestCollector.clan == clan,
            ChestCollector.user_id == user_id,
        )
    )).scalar_one_or_none()
    if existing:
        return existing

    collector = ChestCollector(
        kingdom=kingdom, clan=clan, user_id=user_id,
        slug=secrets.token_urlsafe(16),
    )
    db.add(collector)
    await db.flush()
    return collector


async def _load_aliases(collector_id: int, db: AsyncSession):
    player_aliases = {
        row.raw_name: row.canonical_name
        for row in (await db.execute(
            select(PlayerAlias).where(PlayerAlias.collector_id == collector_id)
        )).scalars().all()
    }
    type_aliases = {
        row.raw_type: row.canonical_type
        for row in (await db.execute(
            select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector_id)
        )).scalars().all()
    }
    return player_aliases, type_aliases


async def _load_existing_keys(collector_id: int, db: AsyncSession):
    return {
        (row.sender_raw, row.chest_type_raw, row.collected_at.isoformat())
        for row in (await db.execute(
            select(Chest).where(Chest.collector_id == collector_id)
        )).scalars().all()
    }


def _dedupe(items, existing_keys):
    """Возвращает только те items, ключ которых ещё не встречался — ни в existing_keys,
    ни среди уже отобранных в этом же вызове (защита от дублей внутри одного батча)."""
    new_items = []
    seen = set(existing_keys)
    for item in items:
        key = (item.sender, item.chest_type, item.timestamp)
        if key in seen:
            continue
        seen.add(key)
        new_items.append(item)
    return new_items


def _build_chest_rows(collector_id: int, items, player_aliases, type_aliases):
    return [
        Chest(
            collector_id=collector_id,
            chest_type_raw=item.chest_type,
            chest_type_canonical=type_aliases.get(item.chest_type, item.chest_type),
            sender_raw=item.sender,
            sender_canonical=player_aliases.get(item.sender, item.sender),
            collected_at=datetime.fromisoformat(item.timestamp),
        )
        for item in items
    ]


async def _charge_chest_import(user_id: int, db: AsyncSession):
    """Атомарно списывает CHEST_IMPORT_COST. Поднимает 402, если кредитов не хватает."""
    row = (await db.execute(
        update(User)
        .where(User.id == user_id, User.credits >= CHEST_IMPORT_COST)
        .values(credits=User.credits - CHEST_IMPORT_COST)
        .returning(User.id, User.credits)
    )).first()
    if not row:
        current = (await db.execute(
            select(User.credits).where(User.id == user_id)
        )).scalar_one()
        raise HTTPException(
            status_code=402,
            detail={
                "message": "Недостаточно кредитов. Пополни баланс.",
                "credits": current,
                "required": CHEST_IMPORT_COST,
            },
        )
    db.add(Transaction(user_id=user_id, type="credit_use", amount=-CHEST_IMPORT_COST,
                       meta={"hunt_type": "chest"}))
    db.add(Hunt(user_id=user_id, hunt_type="chest"))


@router.post("/import")
async def import_chests(payload: ChestImportPayload, db: AsyncSession = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="items is empty")

    user = (await db.execute(
        select(User).where(User.hwid == payload.hwid)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Banned")
    user_id = user.id

    collector = await _get_or_create_collector(payload.kingdom, payload.clan, user_id, db)
    collector_id = collector.id
    collector_slug = collector.slug

    player_aliases, type_aliases = await _load_aliases(collector_id, db)
    existing_keys = await _load_existing_keys(collector_id, db)
    new_items = _dedupe(payload.items, existing_keys)

    if not new_items:
        return {"ok": True, "count": 0, "collector_slug": collector_slug}

    await _charge_chest_import(user_id, db)
    for row in _build_chest_rows(collector_id, new_items, player_aliases, type_aliases):
        db.add(row)

    try:
        await db.commit()
    except IntegrityError:
        # Конкурентная повторная отправка того же батча успела закоммититься между
        # нашим pre-check и нашим commit(). Откатываем (отменяет и списание), пересчитываем
        # коллектора (на случай если это был его первый импорт — INSERT коллектора тоже
        # откатился) и существующие ключи по-настоящему, и пробуем один раз заново.
        await db.rollback()
        collector = await _get_or_create_collector(payload.kingdom, payload.clan, user_id, db)
        collector_id = collector.id
        collector_slug = collector.slug
        existing_keys = await _load_existing_keys(collector_id, db)
        new_items = _dedupe(new_items, existing_keys)
        if not new_items:
            return {"ok": True, "count": 0, "collector_slug": collector_slug}
        await _charge_chest_import(user_id, db)
        for row in _build_chest_rows(collector_id, new_items, player_aliases, type_aliases):
            db.add(row)
        await db.commit()

    return {"ok": True, "count": len(new_items), "collector_slug": collector_slug}


def _pivot_summary(kingdom: str, clan: str, rows) -> dict:
    """rows: iterable of (sender_canonical, chest_type_canonical, count)."""
    chest_types: list[str] = []
    seen_types = set()
    per_player: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {}
    grand_total = 0

    for sender, chest_type, count in rows:
        if chest_type not in seen_types:
            seen_types.add(chest_type)
            chest_types.append(chest_type)
        per_player.setdefault(sender, {})[chest_type] = count
        totals[chest_type] = totals.get(chest_type, 0) + count
        grand_total += count

    players = [
        {"name": name, "counts": counts, "total": sum(counts.values())}
        for name, counts in per_player.items()
    ]
    players.sort(key=lambda p: (-p["total"], p["name"]))
    totals["grand_total"] = grand_total

    return {
        "kingdom": kingdom,
        "clan": clan,
        "chest_types": chest_types,
        "players": players,
        "totals": totals,
    }


@router.get("/summary/{slug}")
async def get_chest_summary(slug: str, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    sender_expr = func.coalesce(PlayerAlias.canonical_name, Chest.sender_raw)
    chest_type_expr = func.coalesce(ChestTypeAlias.canonical_type, Chest.chest_type_raw)

    rows = (await db.execute(
        select(sender_expr, chest_type_expr, func.count())
        .select_from(Chest)
        .outerjoin(
            PlayerAlias,
            and_(PlayerAlias.collector_id == Chest.collector_id,
                 PlayerAlias.raw_name == Chest.sender_raw),
        )
        .outerjoin(
            ChestTypeAlias,
            and_(ChestTypeAlias.collector_id == Chest.collector_id,
                 ChestTypeAlias.raw_type == Chest.chest_type_raw),
        )
        .where(Chest.collector_id == collector.id)
        .group_by(sender_expr, chest_type_expr)
    )).all()

    return _pivot_summary(collector.kingdom, collector.clan, rows)
