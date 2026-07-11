"""
ancients_public.py — публичная (без авторизации) страница «Древнего» для
кланов, которые не ведут учёт Сундуков, но хотят пользоваться калькулятором
квот. Аналог публичной части chests.py (GET /summary/{slug}), только для
ростера Древнего.

Запись данных игроками (звание/состав войск) идёт НЕ через этот файл, а
через уже существующий POST /api/v1/chests/public/player-profile —
PlayerProfile — общая таблица с Сундуками (тот же collector), новый
мутирующий эндпоинт не нужен.

Наружу не выставляются raw_ocr_name/mapped_name/suggested_name/
mapping_confirmed — это исключительно внутренний инструмент лидера в личном
кабинете (ancients_dashboard.py), не публичная информация.
"""
from difflib import get_close_matches

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ancient_quota import OFFICER_RANKS, parse_troop_level, shortfall_pct
from database import get_db
from models import (
    AncientCalculation, AncientNameMapping, AncientRoster, ChestCollector,
    PlayerProfile,
)
from roy import next_trade_routes_end

router = APIRouter(prefix="/api/v1/ancients/public", tags=["ancients-public"])


@router.get("/{slug}")
async def get_public_ancients(slug: str, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    latest_calc = (await db.execute(
        select(AncientCalculation)
        .where(AncientCalculation.collector_id == collector.id)
        .order_by(AncientCalculation.computed_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    rows = (await db.execute(
        select(AncientRoster, PlayerProfile.troop_level.label("profile_troop"),
               PlayerProfile.rank.label("profile_rank"))
        .outerjoin(
            PlayerProfile,
            and_(
                PlayerProfile.collector_id == AncientRoster.collector_id,
                PlayerProfile.canonical_name == AncientRoster.player_name,
            )
        )
        .where(AncientRoster.collector_id == collector.id)
        .order_by(AncientRoster.place.asc().nullslast())
    )).all()

    # Only needed to resolve the correct lookup_name for Strategy-B matching
    # below (mirrors _roster_rows in ancients_dashboard.py) — never exposed
    # in the response, see module docstring.
    confirmed_mappings = (await db.execute(
        select(AncientNameMapping).where(
            AncientNameMapping.collector_id == collector.id,
            AncientNameMapping.confirmed == True,
        )
    )).scalars().all()
    confirmed_mappings_dict = {m.raw_ocr_name: m.canonical_name for m in confirmed_mappings}

    roster = []
    for r in rows:
        player_name = r.AncientRoster.player_name
        effective_rank = r.AncientRoster.rank or r.profile_rank
        effective_troop = r.AncientRoster.troop_level or r.profile_troop

        raw_ocr_name = r.AncientRoster.raw_ocr_name
        already_merged = raw_ocr_name is not None and raw_ocr_name != player_name
        if already_merged:
            lookup_name = player_name
        else:
            canonical_name = confirmed_mappings_dict.get(player_name)
            lookup_name = canonical_name if canonical_name is not None else player_name

        quota = None
        if latest_calc is not None:
            if latest_calc.strategy == "A":
                if effective_rank in OFFICER_RANKS:
                    quota = latest_calc.result_json.get("officer_quota")
                elif effective_rank is not None:
                    quota = latest_calc.result_json.get("veteran_quota")
            else:
                match = next(
                    (p for p in latest_calc.result_json.get("players", [])
                     if p["name"] == lookup_name),
                    None,
                )
                if match is not None:
                    quota = match["quota"]

        roster.append({
            "player_name": player_name,
            "rank": effective_rank,
            "troop_level": effective_troop,
            "points": r.AncientRoster.points,
            "quota": quota,
            "shortfall_pct": shortfall_pct(quota, r.AncientRoster.points),
        })

    return {
        "kingdom": collector.kingdom,
        "clan": collector.clan,
        "quota_thresholds": {
            "light_pct": collector.ancient_shortfall_light_pct if collector.ancient_shortfall_light_pct is not None else 10.0,
            "medium_pct": collector.ancient_shortfall_medium_pct if collector.ancient_shortfall_medium_pct is not None else 30.0,
            "critical_pct": collector.ancient_shortfall_critical_pct if collector.ancient_shortfall_critical_pct is not None else 60.0,
        },
        "roster": roster,
    }


class PublicAddSelfPayload(BaseModel):
    player_name: str
    rank: Optional[str] = None
    troop_level: Optional[str] = None


@router.post("/{slug}/roster")
async def public_add_self(slug: str, payload: PublicAddSelfPayload,
                          db: AsyncSession = Depends(get_db)):
    """Lets a clan member add themselves to the roster from the anonymous
    public page — mirrors ancients_dashboard.py's owner-only /roster/manual,
    minus the auth check, for clans led without the bot."""
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    player_name = payload.player_name.strip()
    if not player_name:
        raise HTTPException(status_code=400, detail="player_name required")

    if payload.troop_level is not None:
        try:
            parse_troop_level(payload.troop_level)
        except ValueError:
            raise HTTPException(status_code=400,
                                detail=f"Unknown troop_level: {payload.troop_level!r}")

    existing_names = list((await db.execute(
        select(AncientRoster.player_name).where(AncientRoster.collector_id == collector.id)
    )).scalars().all())
    if player_name in existing_names:
        raise HTTPException(status_code=409, detail="Player already in roster")

    matches = get_close_matches(player_name, existing_names, n=1, cutoff=0.75)
    if matches:
        raise HTTPException(status_code=409, detail={
            "message": "Similar name already in roster",
            "similar_name": matches[0],
        })

    db.add(AncientRoster(
        collector_id=collector.id, player_name=player_name,
        place=None, points=None, troop_level=payload.troop_level,
        rank=payload.rank, source="manual",
        manual_expires_at=next_trade_routes_end(),
    ))
    await db.commit()
    return {"ok": True}
