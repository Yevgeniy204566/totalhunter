"""
clan.py — Clan roster endpoint (ERP Phase 0).

POST /api/v1/clan/roster — UPSERT member list from bot scan.
Auth: Bearer $ADMIN_TOKEN (same token used for admin panel).
"""
import os
import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from database import get_db
from models import ClanMember, ClanRosterEntry, User
from chests import _get_or_create_collector

router = APIRouter(prefix="/api/v1/clan", tags=["clan"])

_bearer = HTTPBearer()
_ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")


def _require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    if not _ADMIN_TOKEN or creds.credentials != _ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


class MemberIn(BaseModel):
    name: str
    rank: str
    might: Optional[int] = None


class RosterPayload(BaseModel):
    collected_at: str
    roster: List[MemberIn]


@router.post("/roster", dependencies=[Depends(_require_auth)])
async def upsert_clan_roster(
    payload: RosterPayload,
    db: AsyncSession = Depends(get_db),
):
    if not payload.roster:
        raise HTTPException(status_code=400, detail="roster is empty")

    now = func.now()
    for member in payload.roster:
        stmt = (
            pg_insert(ClanMember)
            .values(name=member.name, rank=member.rank, might=member.might, updated_at=now)
            .on_conflict_do_update(
                index_elements=["name"],
                set_={"rank": member.rank, "might": member.might, "updated_at": now},
            )
        )
        await db.execute(stmt)

    await db.commit()
    return {"ok": True, "count": len(payload.roster)}


# ── Bot-facing: clan chat roster upload ───────────────────────────────────────

class RosterUploadPayload(BaseModel):
    hwid: str
    kingdom: str
    clan: str
    names: List[str]


@router.post("/roster-upload")
async def upload_clan_roster(
    payload: RosterUploadPayload,
    db: AsyncSession = Depends(get_db),
):
    """Бот отправляет hwid+kingdom+clan+names, сервер делает upsert по raw_name."""
    user = (await db.execute(
        select(User).where(User.hwid == payload.hwid)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if getattr(user, "is_banned", False):
        raise HTTPException(status_code=403, detail="Banned")

    collector = await _get_or_create_collector(payload.kingdom, payload.clan, user.id, db)

    existing = {
        r.raw_name
        for r in (await db.execute(
            select(ClanRosterEntry.raw_name)
            .where(ClanRosterEntry.collector_id == collector.id)
        )).all()
    }

    added = 0
    for name in payload.names:
        name = name.strip()
        if not name or name in existing:
            continue
        if len(name) > 100:
            continue
        db.add(ClanRosterEntry(
            collector_id=collector.id,
            raw_name=name,
            canonical_name=name,
        ))
        added += 1

    await db.commit()
    return {"ok": True, "added": added, "total": len(payload.names)}
