"""
chest_aliases.py — admin endpoint for syncing alias dictionaries from the
"Admin Sheet" (Google Sheets) into player_aliases / chest_type_aliases.

Auth: Bearer $ADMIN_TOKEN (same pattern as clan.py) — this is an owner/admin action,
not something the bot calls on a user's behalf.

Each sync is a full replace for the named collector: existing rows are deleted, then
the payload's rows are inserted. The Sheet is the source of truth.

chest_aliases entries are submitted in the collector's own language (e.g. raw OCR text
fixed to clean Russian), not English. _resolve_chest_aliases translates each row's
canonical_type to the global English ID when one is already known (literal match or via
Localizations); otherwise it stores the submitted text as-is rather than blocking the
sync — an unmatched chest type just isn't normalized across clans/languages until someone
adds its translation to Localizations.
"""
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import ChestCollector, ChestLocalization, ChestTypeAlias, ChestTypeCatalog, PlayerAlias

router = APIRouter(prefix="/api/v1/chests", tags=["chests"])

_bearer = HTTPBearer(auto_error=False)
_ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not _ADMIN_TOKEN or creds is None or creds.credentials != _ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


class PlayerAliasIn(BaseModel):
    raw_name: str
    canonical_name: str


class ChestAliasIn(BaseModel):
    raw_type: str
    canonical_type: str
    enabled: bool = True


class AliasImportPayload(BaseModel):
    collector_slug: str
    player_aliases: List[PlayerAliasIn] = []
    chest_aliases: List[ChestAliasIn] = []
    pattern: Optional[str] = None
    language: Optional[str] = None


async def _load_known_english_ids(db: AsyncSession) -> set:
    """Every canonical_type already known to the system, from either global table —
    used so admins who already type the literal English ID keep working unchanged."""
    catalog_ids = (await db.execute(select(ChestTypeCatalog.canonical_type))).scalars().all()
    localization_ids = (await db.execute(select(ChestLocalization.canonical_type))).scalars().all()
    return set(catalog_ids) | set(localization_ids)


async def _load_localization_map(db: AsyncSession, language: str) -> dict:
    """display_text -> canonical_type for one language, loaded once per import instead
    of one query per row."""
    rows = (await db.execute(
        select(ChestLocalization.display_text, ChestLocalization.canonical_type)
        .where(ChestLocalization.language == language)
    )).all()
    return {display_text: canonical_type for display_text, canonical_type in rows}


def _resolve_one(submitted: str, known_ids: set, localization_map: dict) -> str:
    """Resolves submitted text to the global English ID when one is known; otherwise
    falls back to the submitted text itself so an unmatched chest type never blocks
    the sync — it just isn't normalized across clans/languages until someone adds the
    translation to Localizations."""
    submitted = submitted.strip()
    if submitted in known_ids:
        return submitted
    return localization_map.get(submitted, submitted)


async def _resolve_chest_aliases(items: List[ChestAliasIn], language: Optional[str],
                                  db: AsyncSession) -> List[ChestAliasIn]:
    known_ids = await _load_known_english_ids(db)
    localization_map = await _load_localization_map(db, language) if language else {}

    return [ChestAliasIn(raw_type=item.raw_type,
                         canonical_type=_resolve_one(item.canonical_type, known_ids, localization_map),
                         enabled=item.enabled)
            for item in items]


@router.post("/aliases/import", dependencies=[Depends(_require_auth)])
async def import_aliases(payload: AliasImportPayload, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == payload.collector_slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    collector_id = collector.id
    if payload.pattern is not None:
        collector.pattern = payload.pattern
    if payload.language is not None:
        collector.language = payload.language

    resolved_chest_aliases = await _resolve_chest_aliases(
        payload.chest_aliases, collector.language, db)

    await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == collector_id))
    await db.execute(delete(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector_id))

    for item in payload.player_aliases:
        db.add(PlayerAlias(collector_id=collector_id, raw_name=item.raw_name,
                           canonical_name=item.canonical_name))
    for item in resolved_chest_aliases:
        db.add(ChestTypeAlias(collector_id=collector_id, raw_type=item.raw_type,
                              canonical_type=item.canonical_type, enabled=item.enabled))

    await db.commit()
    return {
        "ok": True,
        "player_aliases": len(payload.player_aliases),
        "chest_aliases": len(resolved_chest_aliases),
    }
