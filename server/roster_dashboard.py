"""
roster_dashboard.py — Web Dashboard для списка участников клана.

GET  /web/dashboard/roster         — все коллекторы пользователя + их roster-записи
POST /web/dashboard/roster/members — bulk-replace roster для одного коллектора

Паттерн: идентичен /web/dashboard/chests/player-aliases, отдельная таблица clan_roster.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import ChestCollector, ClanRosterEntry, User
from web_routes import get_web_user

router = APIRouter(prefix="/web/dashboard/roster", tags=["roster-dashboard"])


# ── helpers ──────────────────────────────────────────────────────────────────

async def _get_own_collector(db: AsyncSession, slug: str, user: User) -> ChestCollector:
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    if collector.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your collector")
    return collector


async def _roster_rows(db: AsyncSession, collector: ChestCollector) -> list:
    entries = (await db.execute(
        select(ClanRosterEntry)
        .where(ClanRosterEntry.collector_id == collector.id)
        .order_by(ClanRosterEntry.raw_name)
    )).scalars().all()
    return [{"raw_name": e.raw_name, "canonical_name": e.canonical_name} for e in entries]


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def get_roster_dashboard(user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collectors = (await db.execute(
        select(ChestCollector).where(ChestCollector.user_id == user.id)
        .order_by(ChestCollector.id)
    )).scalars().all()

    result = []
    for c in collectors:
        result.append({
            "slug":           c.slug,
            "clan":           c.clan,
            "kingdom":        c.kingdom,
            "roster_rows":    await _roster_rows(db, c),
        })

    return {"collectors": result}


class RosterRowIn(BaseModel):
    raw_name: str
    canonical_name: Optional[str] = None


class RosterMembersPayload(BaseModel):
    collector_slug: str
    rows: List[RosterRowIn] = []


@router.post("/members")
async def post_roster_members(payload: RosterMembersPayload,
                              user: User = Depends(get_web_user),
                              db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, payload.collector_slug, user)

    await db.execute(delete(ClanRosterEntry).where(ClanRosterEntry.collector_id == collector.id))

    for row in payload.rows:
        canonical = (row.canonical_name or "").strip()
        if not canonical:
            continue
        db.add(ClanRosterEntry(
            collector_id=collector.id,
            raw_name=row.raw_name,
            canonical_name=canonical,
        ))

    await db.commit()
    return {"ok": True}
