"""
chest_aliases.py — admin endpoint for syncing alias dictionaries from the
"Admin Sheet" (Google Sheets) into player_aliases / chest_type_aliases.

Auth: Bearer $ADMIN_TOKEN (same pattern as clan.py) — this is an owner/admin action,
not something the bot calls on a user's behalf.

Each sync is a full replace for the named collector: existing rows are deleted, then
the payload's rows are inserted. The Sheet is the source of truth.
"""
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import ChestCollector, ChestTypeAlias, PlayerAlias

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


class AliasImportPayload(BaseModel):
    collector_slug: str
    player_aliases: List[PlayerAliasIn] = []
    chest_aliases: List[ChestAliasIn] = []
    pattern: Optional[str] = None
    language: Optional[str] = None


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

    await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == collector_id))
    await db.execute(delete(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector_id))

    for item in payload.player_aliases:
        db.add(PlayerAlias(collector_id=collector_id, raw_name=item.raw_name,
                           canonical_name=item.canonical_name))
    for item in payload.chest_aliases:
        db.add(ChestTypeAlias(collector_id=collector_id, raw_type=item.raw_type,
                              canonical_type=item.canonical_type))

    await db.commit()
    return {
        "ok": True,
        "player_aliases": len(payload.player_aliases),
        "chest_aliases": len(payload.chest_aliases),
    }
