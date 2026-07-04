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
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ancient_quota import OFFICER_RANKS, shortfall_pct
from database import get_db
from models import AncientCalculation, AncientRoster, ChestCollector, PlayerProfile

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

    roster = []
    for r in rows:
        player_name = r.AncientRoster.player_name
        effective_rank = r.AncientRoster.rank or r.profile_rank
        effective_troop = r.AncientRoster.troop_level or r.profile_troop

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
                     if p["name"] == player_name),
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
