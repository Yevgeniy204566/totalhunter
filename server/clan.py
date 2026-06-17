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
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from database import get_db
from models import ClanMember

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
