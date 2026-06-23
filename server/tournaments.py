"""
tournaments.py — Tournament roster import endpoint.

POST /api/v1/tournaments/import — принимает турнирный ростер от бота (tournament_reader.py),
изолирует по тенанту [kingdom, clan, user_id] (тот же ChestCollector, что у Сундуков),
полностью заменяет ancient_roster для этого collector_id: upsert по player_name (place/
points обновляются, troop_level не трогается), удаление строк для игроков, отсутствующих
в новом импорте.

Auth: hwid в payload → User (как /api/v1/chests/import). Бесплатно — не списывает кредиты,
весь функционал «Древний» бесплатен по требованию.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from chests import _get_or_create_collector
from database import get_db
from models import AncientRoster, PlayerAlias, User

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

    player_aliases = {
        row.raw_name: row.canonical_name
        for row in (await db.execute(
            select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
        )).scalars().all()
    }

    incoming_names = set()
    for item in payload.items:
        canonical_name = player_aliases.get(item.name, item.name)
        incoming_names.add(canonical_name)

        existing = (await db.execute(
            select(AncientRoster).where(
                AncientRoster.collector_id == collector.id,
                AncientRoster.player_name == canonical_name,
            )
        )).scalar_one_or_none()
        if existing:
            existing.place = item.place
            existing.points = item.points
        else:
            db.add(AncientRoster(
                collector_id=collector.id, player_name=canonical_name,
                place=item.place, points=item.points, troop_level=None,
            ))

    await db.flush()
    await db.execute(
        delete(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name.not_in(incoming_names),
        )
    )

    await db.commit()
    return {"ok": True, "count": len(payload.items), "collector_slug": collector.slug}
