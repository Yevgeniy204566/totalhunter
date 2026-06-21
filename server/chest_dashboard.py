"""
chest_dashboard.py — self-service Web Dashboard for chest mapping/scoring.

Auth: site session (JWT Bearer via get_web_user) — any logged-in user manages only their
own ChestCollector rows (collector.user_id == current_user.id), no ADMIN_TOKEN involved.

Phase 4: replaces the Google Sheets + ADMIN_TOKEN workflow for chest_type_aliases/
chest_configurations with a UI any clan can use without owner involvement. Player Aliases
and the global Chest Catalog/Localizations Sheets are untouched (see design doc).
"""
import secrets
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import (
    Chest, ChestCollector, ChestConfiguration, ChestLocalization, ChestTypeAlias,
    ChestTypeCatalog, PlayerAlias, User,
)
from web_routes import get_web_user

router = APIRouter(prefix="/web/dashboard/chests", tags=["chest-dashboard"])


async def _load_known_catalog_ids(db: AsyncSession) -> set:
    catalog_ids = (await db.execute(select(ChestTypeCatalog.canonical_type))).scalars().all()
    localization_ids = (await db.execute(select(ChestLocalization.canonical_type))).scalars().all()
    return set(catalog_ids) | set(localization_ids)


async def _load_catalog_options(db: AsyncSession, language: Optional[str]) -> list:
    known_ids = sorted(await _load_known_catalog_ids(db))
    labels = {}
    if language:
        rows = (await db.execute(
            select(ChestLocalization.canonical_type, ChestLocalization.display_text)
            .where(ChestLocalization.language == language)
        )).all()
        labels = dict(rows)
    options = [{"catalog_id": cid, "label": labels.get(cid, cid)} for cid in known_ids]
    options.sort(key=lambda o: o["label"])
    return options


async def _collector_rows(db: AsyncSession, collector: ChestCollector) -> list:
    aliases = (await db.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalars().all()
    configs = (await db.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalars().all()
    config_by_catalog_id = {c.catalog_id: c for c in configs}

    rows = []
    seen_catalog_ids = set()
    for alias in aliases:
        config = config_by_catalog_id.get(alias.catalog_id)
        seen_catalog_ids.add(alias.catalog_id)
        rows.append({
            "raw_type": alias.raw_type, "catalog_id": alias.catalog_id,
            "custom_name": config.custom_name if config else None,
            "points": config.points if config else 0,
            "is_in_pattern": config.is_in_pattern if config else False,
            "counts_toward_quota": config.counts_toward_quota if config else False,
        })
    for config in configs:
        if config.catalog_id in seen_catalog_ids:
            continue
        rows.append({
            "raw_type": None, "catalog_id": config.catalog_id,
            "custom_name": config.custom_name, "points": config.points,
            "is_in_pattern": config.is_in_pattern,
            "counts_toward_quota": config.counts_toward_quota,
        })

    mapped_raw_types = {a.raw_type for a in aliases}
    unmapped = (await db.execute(
        select(Chest.chest_type_raw).distinct()
        .where(Chest.collector_id == collector.id)
    )).scalars().all()
    for raw_type in unmapped:
        if raw_type in mapped_raw_types:
            continue
        rows.append({"raw_type": raw_type, "catalog_id": None, "custom_name": None,
                     "points": 0, "is_in_pattern": False, "counts_toward_quota": False})

    return rows


async def _player_alias_rows(db: AsyncSession, collector: ChestCollector) -> list:
    aliases = (await db.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    rows = [{"raw_name": a.raw_name, "canonical_name": a.canonical_name} for a in aliases]

    mapped_raw_names = {a.raw_name for a in aliases}
    unmapped = (await db.execute(
        select(Chest.sender_raw).distinct()
        .where(Chest.collector_id == collector.id)
    )).scalars().all()
    for raw_name in unmapped:
        if raw_name in mapped_raw_names:
            continue
        rows.append({"raw_name": raw_name, "canonical_name": None})

    return rows


@router.get("")
async def get_dashboard_chests(user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collectors = (await db.execute(
        select(ChestCollector).where(ChestCollector.user_id == user.id)
    )).scalars().all()

    result = []
    for collector in collectors:
        result.append({
            "slug": collector.slug, "kingdom": collector.kingdom, "clan": collector.clan,
            "language": collector.language,
            "public_url": f"https://total-hunter.com/chests/{collector.slug}",
            "rows": await _collector_rows(db, collector),
            "player_alias_rows": await _player_alias_rows(db, collector),
            "catalog_options": await _load_catalog_options(db, collector.language),
            "timezone_offset_minutes": collector.timezone_offset_minutes,
            "period_start": collector.period_start,
            "period_end": collector.period_end,
            "target_points": collector.target_points,
            "target_chests": collector.target_chests,
        })
    return {"collectors": result}


class RowIn(BaseModel):
    raw_type: Optional[str] = None
    catalog_id: Optional[str] = None
    custom_name: Optional[str] = None
    points: int = 0
    is_in_pattern: bool = False
    counts_toward_quota: bool = False


class RowsPayload(BaseModel):
    collector_slug: str
    rows: List[RowIn] = []


async def _get_own_collector(db: AsyncSession, slug: str, user: User) -> ChestCollector:
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    if collector.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your collector")
    return collector


@router.post("/rows")
async def post_dashboard_rows(payload: RowsPayload, user: User = Depends(get_web_user),
                              db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, payload.collector_slug, user)

    known_ids = await _load_known_catalog_ids(db)
    for row in payload.rows:
        if row.catalog_id is not None and row.catalog_id not in known_ids:
            raise HTTPException(status_code=400,
                                detail=f"Unknown catalog_id: {row.catalog_id!r}")

    await db.execute(delete(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id))
    await db.execute(delete(ChestConfiguration).where(
        ChestConfiguration.collector_id == collector.id))

    for row in payload.rows:
        if row.raw_type is not None and row.catalog_id is not None:
            db.add(ChestTypeAlias(collector_id=collector.id, raw_type=row.raw_type,
                                  catalog_id=row.catalog_id))

        if row.catalog_id is not None:
            db.add(ChestConfiguration(collector_id=collector.id, catalog_id=row.catalog_id,
                                      custom_name=row.custom_name, points=row.points,
                                      is_in_pattern=row.is_in_pattern,
                                      counts_toward_quota=row.counts_toward_quota))

    await db.commit()
    return {"ok": True}


class PlayerAliasRowIn(BaseModel):
    raw_name: str
    canonical_name: Optional[str] = None


class PlayerAliasesPayload(BaseModel):
    collector_slug: str
    rows: List[PlayerAliasRowIn] = []


@router.post("/player-aliases")
async def post_player_aliases(payload: PlayerAliasesPayload, user: User = Depends(get_web_user),
                              db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, payload.collector_slug, user)

    await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == collector.id))

    for row in payload.rows:
        canonical = (row.canonical_name or "").strip()
        if not canonical:
            continue
        db.add(PlayerAlias(collector_id=collector.id, raw_name=row.raw_name,
                           canonical_name=canonical))

    await db.commit()
    return {"ok": True}


class CollectorSlugPayload(BaseModel):
    collector_slug: str


@router.post("/management-token")
async def create_management_token(payload: CollectorSlugPayload,
                                   user: User = Depends(get_web_user),
                                   db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, payload.collector_slug, user)
    code = secrets.token_urlsafe(16)
    collector.management_token = code
    await db.commit()
    return {"code": code}


class ClaimPayload(BaseModel):
    code: str


@router.post("/claim")
async def claim_collector(payload: ClaimPayload, user: User = Depends(get_web_user),
                          db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.management_token == payload.code)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Invalid code")
    collector.user_id = user.id
    collector.management_token = None
    await db.commit()
    return {"ok": True, "slug": collector.slug}


class LanguagePayload(BaseModel):
    language: str


@router.patch("/{slug}/language")
async def update_language(slug: str, payload: LanguagePayload,
                          user: User = Depends(get_web_user),
                          db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    collector.language = payload.language
    await db.commit()
    return {"ok": True}


class SeasonSettingsPayload(BaseModel):
    timezone_offset_minutes: Optional[int] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    target_points: Optional[int] = None
    target_chests: Optional[int] = None


@router.patch("/{slug}/season")
async def update_season_settings(slug: str, payload: SeasonSettingsPayload,
                                  user: User = Depends(get_web_user),
                                  db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)

    effective_start = (payload.period_start if payload.period_start is not None
                       else collector.period_start)
    effective_end = (payload.period_end if payload.period_end is not None
                     else collector.period_end)
    if (effective_start is not None and effective_end is not None
            and effective_end <= effective_start):
        raise HTTPException(status_code=400, detail="period_end must be after period_start")

    if payload.timezone_offset_minutes is not None:
        collector.timezone_offset_minutes = payload.timezone_offset_minutes
    if payload.period_start is not None:
        collector.period_start = payload.period_start
    if payload.period_end is not None:
        collector.period_end = payload.period_end
    if payload.target_points is not None:
        collector.target_points = payload.target_points
    if payload.target_chests is not None:
        collector.target_chests = payload.target_chests

    await db.commit()
    return {"ok": True}
