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
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from chest_history import build_history_list, build_history_detail
from chest_summary import pivot_summary, query_summary_rows
from database import get_db
from models import (
    Chest, ChestCollector, ChestTypeAlias, Hunt,
    PlayerAlias, PlayerProfile, Transaction, User,
)

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
            func.lower(ChestCollector.kingdom) == kingdom.lower(),
            func.lower(ChestCollector.clan) == clan.lower(),
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
        row.raw_type: row.catalog_id
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


@router.get("/summary/{slug}")
async def get_chest_summary(slug: str, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    rows = await query_summary_rows(db, collector, collector.period_start, collector.period_end)

    updated_at_query = select(func.max(Chest.collected_at)).where(
        Chest.collector_id == collector.id)
    if collector.period_start is not None:
        updated_at_query = updated_at_query.where(Chest.collected_at >= collector.period_start)
    if collector.period_end is not None:
        updated_at_query = updated_at_query.where(Chest.collected_at <= collector.period_end)
    updated_at = (await db.execute(updated_at_query)).scalar_one_or_none()

    result = pivot_summary(
        collector.kingdom, collector.clan, rows,
        leader_name=collector.leader_canonical_name,
        leader_excluded=frozenset(collector.leader_excluded_catalog_ids or []),
    )

    # Enrich each player with rank + troop_level from player_profiles
    profiles = (await db.execute(
        select(PlayerProfile).where(PlayerProfile.collector_id == collector.id)
    )).scalars().all()
    profile_map = {p.canonical_name: p for p in profiles}
    for player in result["players"]:
        profile = profile_map.get(player["name"])
        player["rank"] = profile.rank if profile else None
        player["troop_level"] = profile.troop_level if profile else None

    result["collector_slug"] = collector.slug
    result["updated_at"] = updated_at.isoformat() if updated_at else None
    result["period_start"] = collector.period_start.isoformat() if collector.period_start else None
    result["period_end"] = collector.period_end.isoformat() if collector.period_end else None
    result["stopped_at"] = collector.stopped_at.isoformat() if collector.stopped_at else None
    result["timezone_offset_minutes"] = collector.timezone_offset_minutes
    result["targets"] = {
        "points": collector.target_points,
        "chests": collector.target_chests,
    }
    return result


def _clan_to_slug(clan: str) -> str:
    import re
    return re.sub(r'[^a-z0-9]+', '-', clan.lower()).strip('-')


_PUBLIC_PROFILE_COOLDOWN = timedelta(hours=6)

_VALID_RANKS = {"Глава", "Старший", "Офицер", "Ветеран", "Рядовой"}
# G/S/M + тир 1-9 каждый, через пробел: "G8 S7 M8"
_TROOP_RE = re.compile(r'^G[1-9] S[1-9] M[1-9]$')


class PublicPlayerProfileIn(BaseModel):
    collector_slug: str
    canonical_name: str
    rank: Optional[str] = None
    troop_level: Optional[str] = None


@router.post("/public/player-profile")
async def public_upsert_player_profile(payload: PublicPlayerProfileIn,
                                       db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == payload.collector_slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    canonical = (payload.canonical_name or "").strip()
    if not canonical:
        raise HTTPException(status_code=400, detail="canonical_name required")

    rank = (payload.rank or "").strip() or None
    troop = (payload.troop_level or "").strip() or None
    if rank and rank not in _VALID_RANKS:
        raise HTTPException(status_code=422, detail="Недопустимое звание")
    if troop and not _TROOP_RE.match(troop):
        raise HTTPException(status_code=422, detail="Недопустимый состав войск")

    existing = (await db.execute(
        select(PlayerProfile).where(
            PlayerProfile.collector_id == collector.id,
            PlayerProfile.canonical_name == canonical,
        )
    )).scalar_one_or_none()

    if existing:
        # Anti-flood: публичный эндпоинт анонимный, кулдаун защищает от перебивания чужих данных
        now = datetime.now(timezone.utc)
        updated = existing.updated_at
        if updated is not None:
            # SQLite (тесты) возвращает naive datetime — нормализуем
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            elapsed = now - updated
            if elapsed < _PUBLIC_PROFILE_COOLDOWN:
                wait_min = int((_PUBLIC_PROFILE_COOLDOWN - elapsed).total_seconds() / 60) + 1
                raise HTTPException(status_code=429,
                                    detail=f"Повторное сохранение доступно через {wait_min} мин.")
        existing.rank = rank
        existing.troop_level = troop
        existing.updated_at = now
    else:
        db.add(PlayerProfile(
            collector_id=collector.id,
            canonical_name=canonical,
            rank=rank,
            troop_level=troop,
        ))

    await db.commit()
    return {"ok": True}


@router.get("/by/{kingdom}/{custom_slug}")
async def get_chest_by_kingdom_slug(kingdom: str, custom_slug: str,
                                    db: AsyncSession = Depends(get_db)):
    collectors = (await db.execute(
        select(ChestCollector).where(
            func.lower(ChestCollector.kingdom) == kingdom.lower(),
        )
    )).scalars().all()
    collector = next((c for c in collectors if _clan_to_slug(c.clan) == custom_slug.lower()), None)
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    rows = await query_summary_rows(db, collector, collector.period_start, collector.period_end)

    updated_at_query = select(func.max(Chest.collected_at)).where(
        Chest.collector_id == collector.id)
    if collector.period_start is not None:
        updated_at_query = updated_at_query.where(Chest.collected_at >= collector.period_start)
    if collector.period_end is not None:
        updated_at_query = updated_at_query.where(Chest.collected_at <= collector.period_end)
    updated_at = (await db.execute(updated_at_query)).scalar_one_or_none()

    result = pivot_summary(
        collector.kingdom, collector.clan, rows,
        leader_name=collector.leader_canonical_name,
        leader_excluded=frozenset(collector.leader_excluded_catalog_ids or []),
    )

    # Enrich each player with rank + troop_level from player_profiles
    profiles = (await db.execute(
        select(PlayerProfile).where(PlayerProfile.collector_id == collector.id)
    )).scalars().all()
    profile_map = {p.canonical_name: p for p in profiles}
    for player in result["players"]:
        profile = profile_map.get(player["name"])
        player["rank"] = profile.rank if profile else None
        player["troop_level"] = profile.troop_level if profile else None

    result["collector_slug"] = collector.slug
    result["updated_at"] = updated_at.isoformat() if updated_at else None
    result["period_start"] = collector.period_start.isoformat() if collector.period_start else None
    result["period_end"] = collector.period_end.isoformat() if collector.period_end else None
    result["stopped_at"] = collector.stopped_at.isoformat() if collector.stopped_at else None
    result["timezone_offset_minutes"] = collector.timezone_offset_minutes
    result["targets"] = {
        "points": collector.target_points,
        "chests": collector.target_chests,
    }
    return result


@router.get("/history/{slug}")
async def list_chest_history(slug: str, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    return {"seasons": await build_history_list(db, collector.id)}


@router.get("/history/{slug}/{season_id}")
async def get_chest_history_detail(slug: str, season_id: int, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    detail = await build_history_detail(db, collector.id, season_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Season not found")
    return detail
