"""
tournaments.py — Tournament roster import endpoint.

POST /api/v1/tournaments/import — принимает турнирный ростер от бота (tournament_reader.py),
изолирует по тенанту [kingdom, clan, user_id] (тот же ChestCollector, что у Сундуков),
полностью заменяет ancient_roster для этого collector_id: upsert по player_name (place/
points обновляются, troop_level не трогается), удаление строк для игроков, отсутствующих
в новом импорте.

Резолвинг сырого OCR-имени в каноническое происходит ТОЛЬКО через уже подтверждённый на
дашборде AncientNameMapping (raw_ocr_name -> canonical_name, confirmed=True) — никакого
fuzzy-угадывания на импорте больше нет. Не подтверждённое лидером сырое имя сохраняется
как есть (в player_name и в raw_ocr_name) и ждёт ручного сопоставления на дашборде
(ancients_dashboard.py), которое сливает физические строки при подтверждении.

Auth: hwid в payload → User (как /api/v1/chests/import). Бесплатно — не списывает кредиты,
весь функционал «Древний» бесплатен по требованию.
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chests import _get_or_create_collector
from database import get_db
from models import AncientNameMapping, AncientRoster, Log, User

router = APIRouter(prefix="/api/v1/tournaments", tags=["tournaments"])


class TournamentItemIn(BaseModel):
    name: str
    place: Optional[int] = None
    points: Optional[int] = None


class TournamentImportPayload(BaseModel):
    hwid: str
    kingdom: str
    clan: str
    timestamp: str
    items: List[TournamentItemIn]


@router.post("/import")
async def import_tournament(payload: TournamentImportPayload,
                            db: AsyncSession = Depends(get_db)):
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
    if collector.ancient_hidden:
        collector.ancient_hidden_at = datetime.now(timezone.utc)

    confirmed_mappings = {
        m.raw_ocr_name: m.canonical_name
        for m in (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id,
                AncientNameMapping.confirmed == True,
            )
        )).scalars().all()
    }

    incoming_names = set()
    for item in payload.items:
        target_name = confirmed_mappings.get(item.name, item.name)
        incoming_names.add(target_name)

        existing = (await db.execute(
            select(AncientRoster).where(
                AncientRoster.collector_id == collector.id,
                AncientRoster.player_name == target_name,
            )
        )).scalar_one_or_none()
        if existing:
            existing.place = item.place
            existing.points = item.points
            existing.source = "ocr"
            existing.manual_expires_at = None
            existing.raw_ocr_name = item.name
        else:
            db.add(AncientRoster(
                collector_id=collector.id, player_name=target_name,
                place=item.place, points=item.points, troop_level=None,
                source="ocr", raw_ocr_name=item.name,
            ))

    await db.flush()
    stale_rows = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name.not_in(incoming_names),
            AncientRoster.source == "ocr",
        )
    )).scalars().all()
    for row in stale_rows:
        if row.troop_level is None and row.rank is None:
            await db.delete(row)
        else:
            row.place = None
            row.points = None

    db.add(Log(hwid=user.hwid, event_type="ancient_ocr_import"))

    await db.commit()
    return {"ok": True, "count": len(payload.items), "collector_slug": collector.slug}
