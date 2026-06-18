"""
chests.py — Сундуки (Chests) import endpoint.

POST /api/v1/chests/import — принимает батч сундуков от бота, изолирует данные по
тенанту [kingdom, clan, user_id] (ChestCollector) и применяет alias-словари сборщика
к имени игрока и типу сундука перед записью.

Auth: hwid в payload → User (как /use_credit), НЕ Bearer ADMIN_TOKEN — вызывается
рядовыми платящими пользователями бота, а не админ-скриптами.
"""
import secrets
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Chest, ChestCollector, ChestTypeAlias, PlayerAlias, User

router = APIRouter(prefix="/api/v1/chests", tags=["chests"])


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

    collector = await _get_or_create_collector(payload.kingdom, payload.clan, user.id, db)

    player_aliases = {
        row.raw_name: row.canonical_name
        for row in (await db.execute(
            select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
        )).scalars().all()
    }
    type_aliases = {
        row.raw_type: row.canonical_type
        for row in (await db.execute(
            select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
        )).scalars().all()
    }

    existing_keys = {
        (row.sender_raw, row.chest_type_raw, row.collected_at.isoformat())
        for row in (await db.execute(
            select(Chest).where(Chest.collector_id == collector.id)
        )).scalars().all()
    }

    inserted = 0
    for item in payload.items:
        key = (item.sender, item.chest_type, item.timestamp)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        db.add(Chest(
            collector_id=collector.id,
            chest_type_raw=item.chest_type,
            chest_type_canonical=type_aliases.get(item.chest_type, item.chest_type),
            sender_raw=item.sender,
            sender_canonical=player_aliases.get(item.sender, item.sender),
            collected_at=datetime.fromisoformat(item.timestamp),
        ))
        inserted += 1

    await db.commit()

    return {"ok": True, "count": inserted, "collector_slug": collector.slug}
