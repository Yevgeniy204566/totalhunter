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
import difflib
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from chests import _get_or_create_collector
from database import get_db
from models import AncientRoster, PlayerAlias, User

router = APIRouter(prefix="/api/v1/tournaments", tags=["tournaments"])

# Tournament OCR (tournament_reader.py) has no manual-correction system of its own —
# unlike chest sender names, which get fixed once via PlayerAlias and stay fixed
# forever. Same-script noise (a name read correctly, plus leftover badge-icon
# garbage like "Бандеролька __") is common enough to be worth auto-cleaning: if the
# raw OCR name isn't an exact alias hit, fall back to fuzzy-matching it against this
# collector's already-confirmed PlayerAlias canonical names (curated via the Chests
# dashboard) and use that instead when the match is close enough.
#
# This does NOT fix full cross-script misreads (Tesseract reading a Cyrillic name as
# Latin glyphs, e.g. "Marisha?" for "Маришка") — those score ~0 similarity against the
# Cyrillic canonical name since the character sets don't overlap at all. Transliteration-
# aware matching would be needed for that and was deliberately not attempted here: the
# many-to-many mapping (e.g. "x" -> "х" or "кс") risks confidently matching the wrong
# player, which is worse than leaving an obviously-garbled name for manual review.
NAME_FUZZY_MATCH_CUTOFF = 0.75


def _resolve_player_name(raw_name: str, player_aliases: dict, canonical_by_fold: dict) -> str:
    if raw_name in player_aliases:
        return player_aliases[raw_name]
    matches = difflib.get_close_matches(
        raw_name.casefold(), canonical_by_fold.keys(), n=1, cutoff=NAME_FUZZY_MATCH_CUTOFF)
    return canonical_by_fold[matches[0]] if matches else raw_name


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
    if collector.ancient_hidden_at is not None:
        collector.ancient_hidden_at = datetime.now(timezone.utc)

    player_aliases = {
        row.raw_name: row.canonical_name
        for row in (await db.execute(
            select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
        )).scalars().all()
    }
    canonical_by_fold = {name.casefold(): name for name in set(player_aliases.values())}

    incoming_names = set()
    for item in payload.items:
        canonical_name = _resolve_player_name(item.name, player_aliases, canonical_by_fold)
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
