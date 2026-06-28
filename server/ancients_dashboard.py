"""
ancients_dashboard.py — Личный кабинет, вкладка «Древний».

Auth: site session (JWT Bearer via get_web_user), как chest_dashboard.py — лидер
управляет только своими ChestCollector. Бесплатно для всех пользователей.
"""
from difflib import get_close_matches
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ancient_quota import (
    ANCIENT_LEVEL_HP, TROOP_QUOTA_PRESETS, TROOP_STEPS,
    split_strategy_a, split_strategy_b, total_quota_millions,
)
from database import get_db
from models import (
    AncientCalculation, AncientNameMapping, AncientRoster,
    ChestCollector, PlayerAlias, PlayerProfile, User,
)
from web_routes import get_web_user

router = APIRouter(prefix="/web/dashboard/ancients", tags=["ancients-dashboard"])

HISTORY_LIMIT = 5


async def _get_own_collector(db: AsyncSession, slug: str, user: User) -> ChestCollector:
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    if collector.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your collector")
    return collector


async def _roster_rows(
    db: AsyncSession,
    collector_id: int,
    mappings_dict: dict,        # raw_ocr_name → AncientNameMapping
    canonical_names: list,
    fuzzy_threshold: float,
) -> list:
    rows = (await db.execute(
        select(AncientRoster, PlayerProfile.troop_level.label("profile_troop"))
        .outerjoin(
            PlayerProfile,
            and_(
                PlayerProfile.collector_id == AncientRoster.collector_id,
                PlayerProfile.canonical_name == AncientRoster.player_name,
            )
        )
        .where(AncientRoster.collector_id == collector_id)
        .order_by(AncientRoster.place.asc().nullslast())
    )).all()

    result = []
    for r in rows:
        raw = r.AncientRoster.player_name
        mapping = mappings_dict.get(raw)
        if mapping and mapping.confirmed:
            mapped_name = mapping.canonical_name
            suggested_name = None
            confirmed = True
        else:
            mapped_name = None
            matches = get_close_matches(raw, canonical_names, n=1, cutoff=fuzzy_threshold)
            suggested_name = matches[0] if matches else None
            confirmed = False
        result.append({
            "player_name": raw,
            "place": r.AncientRoster.place,
            "points": r.AncientRoster.points,
            "troop_level": r.AncientRoster.troop_level or r.profile_troop,
            "mapped_name": mapped_name,
            "suggested_name": suggested_name,
            "mapping_confirmed": confirmed,
            "is_alias_source": suggested_name is not None,  # True = авто-найдено из Сундуков
        })
    return result


async def _history_rows(db: AsyncSession, collector_id: int) -> list:
    rows = (await db.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector_id)
        .order_by(AncientCalculation.computed_at.desc())
    )).scalars().all()
    return [
        {"id": r.id, "computed_at": r.computed_at.isoformat(), "strategy": r.strategy,
         "summon_levels": r.summon_levels, "clan_preset": r.clan_preset,
         "amplification_coef": r.amplification_coef,
         "officer_count": r.officer_count, "veteran_count": r.veteran_count,
         "total_quota_millions": r.total_quota_millions, "result": r.result_json}
        for r in rows
    ]


@router.get("")
async def get_dashboard_ancients(
    fuzzy_threshold: float = Query(default=0.75, ge=0.5, le=1.0),
    user: User = Depends(get_web_user),
    db: AsyncSession = Depends(get_db),
):
    collectors = (await db.execute(
        select(ChestCollector).where(ChestCollector.user_id == user.id)
    )).scalars().all()

    result = []
    for collector in collectors:
        canonical_names = list((await db.execute(
            select(PlayerAlias.canonical_name).where(
                PlayerAlias.collector_id == collector.id)
        )).scalars().all())

        mappings = (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id)
        )).scalars().all()
        mappings_dict = {m.raw_ocr_name: m for m in mappings}

        result.append({
            "slug": collector.slug,
            "kingdom": collector.kingdom,
            "clan": collector.clan,
            "canonical_names": canonical_names,
            "roster": await _roster_rows(
                db, collector.id, mappings_dict, canonical_names, fuzzy_threshold),
            "history": await _history_rows(db, collector.id),
            "troop_steps": TROOP_STEPS,
            "presets": sorted(TROOP_QUOTA_PRESETS.keys()),
        })
    return {"collectors": result, "ancient_level_hp": ANCIENT_LEVEL_HP}


class TroopLevelPayload(BaseModel):
    player_name: str
    troop_level: Optional[str] = None


@router.patch("/{slug}/troop-level")
async def patch_troop_level(slug: str, payload: TroopLevelPayload,
                            user: User = Depends(get_web_user),
                            db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    if payload.troop_level is not None and payload.troop_level not in TROOP_STEPS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown troop_level: {payload.troop_level!r}")

    row = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == payload.player_name,
        )
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Player not in roster")

    row.troop_level = payload.troop_level
    await db.commit()
    return {"ok": True}


class CalculatePayload(BaseModel):
    strategy: str
    summon_levels: List[int]
    amplification_coef: float
    clan_preset: Optional[str] = None
    officer_count: Optional[int] = None
    veteran_count: Optional[int] = None


@router.post("/{slug}/calculate")
async def calculate(slug: str, payload: CalculatePayload,
                    user: User = Depends(get_web_user),
                    db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)

    if payload.strategy not in ("A", "B"):
        raise HTTPException(status_code=400, detail="strategy must be 'A' or 'B'")
    if not payload.summon_levels or len(payload.summon_levels) > 6:
        raise HTTPException(status_code=400, detail="summon_levels must have 1-6 entries")

    total = total_quota_millions(payload.summon_levels, payload.amplification_coef)

    if payload.strategy == "A":
        if payload.officer_count is None or payload.veteran_count is None:
            raise HTTPException(status_code=400,
                                detail="officer_count and veteran_count are required for strategy A")
        try:
            result = split_strategy_a(total, payload.officer_count, payload.veteran_count)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        if payload.clan_preset not in TROOP_QUOTA_PRESETS:
            raise HTTPException(status_code=400, detail="clan_preset must be one of T5-T9")
        roster = (await db.execute(
            select(AncientRoster).where(AncientRoster.collector_id == collector.id)
        )).scalars().all()
        players = [(r.player_name, r.troop_level) for r in roster]
        try:
            result = split_strategy_b(total, payload.clan_preset, players)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    db.add(AncientCalculation(
        collector_id=collector.id, strategy=payload.strategy,
        clan_preset=payload.clan_preset, summon_levels=payload.summon_levels,
        amplification_coef=payload.amplification_coef,
        officer_count=payload.officer_count, veteran_count=payload.veteran_count,
        total_quota_millions=total, result_json=result,
    ))
    await db.flush()

    history_ids = (await db.execute(
        select(AncientCalculation.id)
        .where(AncientCalculation.collector_id == collector.id)
        .order_by(AncientCalculation.computed_at.desc())
    )).scalars().all()
    if len(history_ids) > HISTORY_LIMIT:
        stale_ids = history_ids[HISTORY_LIMIT:]
        await db.execute(delete(AncientCalculation).where(
            AncientCalculation.id.in_(stale_ids)))

    await db.commit()
    return {"total_quota_millions": total, "result": result}
