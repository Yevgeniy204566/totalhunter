"""
ancients_dashboard.py — Личный кабинет, вкладка «Древний».

Auth: site session (JWT Bearer via get_web_user), как chest_dashboard.py — лидер
управляет только своими ChestCollector. Бесплатно для всех пользователей.

Редакторы: сокланы с активным AncientEditor-записью могут редактировать состав войск
и маппинги, но не запускать калькулятор. Доступ выдаётся через одноразовый invite-код
(TTL 24ч), и действует 30 дней с момента принятия.
"""
import secrets
from datetime import datetime, timedelta, timezone
from difflib import get_close_matches
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ancient_quota import (
    ANCIENT_LEVEL_HP, OFFICER_RANKS, RANKS, VALID_PRESETS, parse_troop_level,
    shortfall_pct, split_strategy_a, split_strategy_b, total_quota_millions,
)
from database import get_db
from models import (
    AncientCalculation, AncientEditor, AncientInviteCode,
    AncientNameMapping, AncientRoster,
    ChestCollector, Log, PlayerAlias, PlayerProfile, User,
)
from roy import next_trade_routes_end
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


async def _get_own_or_editor_collector(
    db: AsyncSession, slug: str, user: User
) -> tuple[ChestCollector, bool]:
    """Returns (collector, is_owner). Raises 403 if user has no access at all."""
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    if collector.user_id == user.id:
        return collector, True
    now = datetime.now(timezone.utc)
    editor = (await db.execute(
        select(AncientEditor).where(
            AncientEditor.collector_id == collector.id,
            AncientEditor.user_id == user.id,
            AncientEditor.expires_at > now,
        )
    )).scalar_one_or_none()
    if editor:
        return collector, False
    raise HTTPException(status_code=403, detail="Not your collector")


async def _roster_rows(
    db: AsyncSession,
    collector_id: int,
    mappings_dict: dict,        # raw_ocr_name → AncientNameMapping
    canonical_names: list,
    fuzzy_threshold: float,
    latest_calc,                # Optional[AncientCalculation]
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

        quota = None
        if latest_calc is not None:
            if latest_calc.strategy == "A":
                rank = r.AncientRoster.rank
                if rank in OFFICER_RANKS:
                    quota = latest_calc.result_json.get("officer_quota")
                elif rank is not None:
                    quota = latest_calc.result_json.get("veteran_quota")
            else:
                lookup_name = mapped_name if confirmed else raw
                match = next(
                    (p for p in latest_calc.result_json.get("players", [])
                     if p["name"] == lookup_name),
                    None,
                )
                if match is not None:
                    quota = match["quota"]

        result.append({
            "player_name": raw,
            "place": r.AncientRoster.place,
            "points": r.AncientRoster.points,
            "troop_level": r.AncientRoster.troop_level or r.profile_troop,
            "rank": r.AncientRoster.rank,
            "quota": quota,
            "shortfall_pct": shortfall_pct(quota, r.AncientRoster.points),
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
    own_collectors_all = (await db.execute(
        select(ChestCollector).where(ChestCollector.user_id == user.id)
        .order_by(ChestCollector.id.desc())
    )).scalars().all()
    own_collectors = [c for c in own_collectors_all if not c.ancient_hidden]
    own_hidden = [c for c in own_collectors_all if c.ancient_hidden]

    now = datetime.now(timezone.utc)
    editor_rows = (await db.execute(
        select(AncientEditor, ChestCollector)
        .join(ChestCollector, ChestCollector.id == AncientEditor.collector_id)
        .where(
            AncientEditor.user_id == user.id,
            AncientEditor.expires_at > now,
        )
        .order_by(ChestCollector.id.desc())
    )).all()
    own_ids = {c.id for c in own_collectors}
    editor_collectors = [row.ChestCollector for row in editor_rows if row.ChestCollector.id not in own_ids]

    # (collector, is_owner) pairs
    all_pairs: list[tuple[ChestCollector, bool]] = (
        [(c, True) for c in own_collectors] + [(c, False) for c in editor_collectors]
    )

    all_canonical: dict[str, list[str]] = {}
    for c, _ in all_pairs:
        names = list((await db.execute(
            select(PlayerAlias.canonical_name).where(PlayerAlias.collector_id == c.id)
        )).scalars().all())
        all_canonical[c.slug] = names

    canonical_sources = [
        {"slug": c.slug, "clan": c.clan, "kingdom": c.kingdom,
         "canonical_names": all_canonical[c.slug]}
        for c, _ in all_pairs
    ]

    result = []
    for collector, is_owner in all_pairs:
        canonical_names = all_canonical[collector.slug]

        mappings = (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id)
        )).scalars().all()
        mappings_dict = {m.raw_ocr_name: m for m in mappings}

        latest_calc = (await db.execute(
            select(AncientCalculation)
            .where(AncientCalculation.collector_id == collector.id)
            .order_by(AncientCalculation.computed_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        result.append({
            "slug": collector.slug,
            "kingdom": collector.kingdom,
            "clan": collector.clan,
            "is_owner": is_owner,
            "canonical_names": canonical_names,
            "roster": await _roster_rows(
                db, collector.id, mappings_dict, canonical_names, fuzzy_threshold,
                latest_calc),
            "history": await _history_rows(db, collector.id),
            "presets": sorted(VALID_PRESETS),
            "quota_thresholds": {
                "light_pct": collector.ancient_shortfall_light_pct if collector.ancient_shortfall_light_pct is not None else 10.0,
                "medium_pct": collector.ancient_shortfall_medium_pct if collector.ancient_shortfall_medium_pct is not None else 30.0,
                "critical_pct": collector.ancient_shortfall_critical_pct if collector.ancient_shortfall_critical_pct is not None else 60.0,
            },
        })
    hidden_collectors = [
        {"slug": c.slug, "kingdom": c.kingdom, "clan": c.clan} for c in own_hidden
    ]
    return {"collectors": result, "canonical_sources": canonical_sources,
            "ancient_level_hp": ANCIENT_LEVEL_HP, "hidden_collectors": hidden_collectors}


class VisibilityPayload(BaseModel):
    hidden: bool


@router.patch("/{slug}/ancient-visibility")
async def set_ancient_visibility(slug: str, payload: VisibilityPayload,
                                 user: User = Depends(get_web_user),
                                 db: AsyncSession = Depends(get_db)):
    """Скрыть/показать коллектор во вкладке «Древний» — не удаляет данные.
    Коллектор общий с Сундуками, поэтому это только owner-view preference,
    не влияет на доступ редакторов и не трогает данные Сундуков."""
    collector = await _get_own_collector(db, slug, user)
    collector.ancient_hidden = payload.hidden
    collector.ancient_hidden_at = datetime.now(timezone.utc) if payload.hidden else None
    await db.commit()
    return {"ok": True}


class QuotaThresholdsPayload(BaseModel):
    light_pct: float
    medium_pct: float
    critical_pct: float


@router.patch("/{slug}/quota-thresholds")
async def set_quota_thresholds(slug: str, payload: QuotaThresholdsPayload,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    collector.ancient_shortfall_light_pct = payload.light_pct
    collector.ancient_shortfall_medium_pct = payload.medium_pct
    collector.ancient_shortfall_critical_pct = payload.critical_pct
    await db.commit()
    return {"ok": True}


class TroopLevelPayload(BaseModel):
    player_name: str
    troop_level: Optional[str] = None


@router.patch("/{slug}/troop-level")
async def patch_troop_level(slug: str, payload: TroopLevelPayload,
                            user: User = Depends(get_web_user),
                            db: AsyncSession = Depends(get_db)):
    collector, _ = await _get_own_or_editor_collector(db, slug, user)
    if payload.troop_level is not None:
        try:
            parse_troop_level(payload.troop_level)
        except ValueError:
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


class RankPayload(BaseModel):
    player_name: str
    rank: Optional[str] = None


@router.patch("/{slug}/rank")
async def patch_rank(slug: str, payload: RankPayload,
                     user: User = Depends(get_web_user),
                     db: AsyncSession = Depends(get_db)):
    collector, _ = await _get_own_or_editor_collector(db, slug, user)
    if payload.rank is not None and payload.rank not in RANKS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown rank: {payload.rank!r}")

    row = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == payload.player_name,
        )
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Player not in roster")

    row.rank = payload.rank
    await db.commit()
    return {"ok": True}


class NameMappingItem(BaseModel):
    raw_ocr_name: str
    canonical_name: str
    confirmed: bool = True


class NameMappingsPayload(BaseModel):
    mappings: List[NameMappingItem]


@router.patch("/{slug}/name-mappings")
async def patch_name_mappings(slug: str, payload: NameMappingsPayload,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector, _ = await _get_own_or_editor_collector(db, slug, user)
    for item in payload.mappings:
        existing = (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id,
                AncientNameMapping.raw_ocr_name == item.raw_ocr_name,
            )
        )).scalar_one_or_none()
        if existing:
            existing.canonical_name = item.canonical_name
            existing.confirmed = item.confirmed
        else:
            db.add(AncientNameMapping(
                collector_id=collector.id,
                raw_ocr_name=item.raw_ocr_name,
                canonical_name=item.canonical_name,
                confirmed=item.confirmed,
            ))
    await db.commit()
    return {"ok": True}


@router.delete("/{slug}/name-mappings/{raw_ocr_name}")
async def delete_name_mapping(slug: str, raw_ocr_name: str,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector, _ = await _get_own_or_editor_collector(db, slug, user)
    existing = (await db.execute(
        select(AncientNameMapping).where(
            AncientNameMapping.collector_id == collector.id,
            AncientNameMapping.raw_ocr_name == raw_ocr_name,
        )
    )).scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Mapping not found")
    await db.execute(
        delete(AncientNameMapping).where(
            AncientNameMapping.collector_id == collector.id,
            AncientNameMapping.raw_ocr_name == raw_ocr_name,
        )
    )
    await db.commit()
    return {"deleted": True}


@router.delete("/{slug}/roster/{player_name}")
async def delete_roster_entry(slug: str, player_name: str,
                              user: User = Depends(get_web_user),
                              db: AsyncSession = Depends(get_db)):
    """Удаление игрока из ростера Древнего вручную — например, если он ушёл
    из клана и больше не будет участвовать в турнирах («мёртвые души» не
    должны получать квоту урона)."""
    collector, _ = await _get_own_or_editor_collector(db, slug, user)
    existing = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == player_name,
        )
    )).scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Player not in roster")
    await db.execute(
        delete(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == player_name,
        )
    )
    await db.commit()
    return {"deleted": True}


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
    if collector.ancient_hidden:
        collector.ancient_hidden_at = datetime.now(timezone.utc)

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
        if payload.clan_preset not in VALID_PRESETS:
            raise HTTPException(status_code=400, detail="clan_preset must be one of T5-T9")
        roster = (await db.execute(
            select(AncientRoster).where(AncientRoster.collector_id == collector.id)
        )).scalars().all()
        confirmed_mappings = (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id,
                AncientNameMapping.confirmed == True,
            )
        )).scalars().all()
        mapped_names = {m.raw_ocr_name: m.canonical_name for m in confirmed_mappings}
        players = [(mapped_names.get(r.player_name, r.player_name), r.troop_level) for r in roster]
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

    db.add(Log(hwid=user.hwid, event_type="ancient_quota_calc"))

    await db.commit()
    return {"total_quota_millions": total, "result": result}


class ManualRosterPayload(BaseModel):
    player_name: str
    troop_level: Optional[str] = None
    rank: Optional[str] = None


@router.post("/{slug}/roster/manual")
async def add_manual_roster_entry(slug: str, payload: ManualRosterPayload,
                                  user: User = Depends(get_web_user),
                                  db: AsyncSession = Depends(get_db)):
    """Ручное добавление участника Древнего — для игроков, которых нет ни
    в турнирной таблице (OCR), ни в базе Сундуков. Сгорает на ближайшем
    завершении «Торговых Путей», если реальные данные так и не появятся."""
    collector, _ = await _get_own_or_editor_collector(db, slug, user)

    if payload.troop_level is not None:
        try:
            parse_troop_level(payload.troop_level)
        except ValueError:
            raise HTTPException(status_code=400,
                                detail=f"Unknown troop_level: {payload.troop_level!r}")

    existing = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == payload.player_name,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Player already in roster")

    canonical_names = list((await db.execute(
        select(PlayerAlias.canonical_name).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all())
    matches = get_close_matches(payload.player_name, canonical_names, n=1, cutoff=0.75)
    if matches and matches[0] != payload.player_name:
        raise HTTPException(status_code=409, detail={
            "message": "Similar name already confirmed",
            "similar_name": matches[0],
        })

    db.add(AncientRoster(
        collector_id=collector.id, player_name=payload.player_name,
        place=None, points=None, troop_level=payload.troop_level,
        rank=payload.rank, source="manual",
        manual_expires_at=next_trade_routes_end(),
    ))
    await db.commit()
    return {"ok": True}


@router.post("/{slug}/roster/populate-from-chests")
async def populate_roster_from_chests(slug: str,
                                      user: User = Depends(get_web_user),
                                      db: AsyncSession = Depends(get_db)):
    """Отзеркалить точный список имён из базы Сундуков в ростер Древнего —
    ровно одна строка на канонического игрока. Сырая OCR-строка с
    подтверждённым сопоставлением («Правильное имя») переносит свои данные
    (место/очки/состав/звание) под каноническое имя. Любая строка без
    подтверждённого соответствия и без точного совпадения с базой Сундуков
    удаляется целиком — по явному требованию владельца («заменить всё,
    точная копия имён Сундуков»). Это относится и к вручную добавленным
    записям (source='manual') — если игрока нет в Сундуках, эта кнопка его
    уберёт; для не-носящих сундуки участников Древнего это осознанный
    компромисс владельца, не баг."""
    collector, _ = await _get_own_or_editor_collector(db, slug, user)

    canonical_names = list(dict.fromkeys((await db.execute(
        select(PlayerAlias.canonical_name).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()))
    canonical_set = set(canonical_names)

    mappings = (await db.execute(
        select(AncientNameMapping).where(
            AncientNameMapping.collector_id == collector.id,
            AncientNameMapping.confirmed == True,
        )
    )).scalars().all()
    raw_to_canonical = {m.raw_ocr_name: m.canonical_name for m in mappings}

    roster_rows = (await db.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()

    preserved: dict[str, dict] = {}
    removed = 0
    for row in roster_rows:
        target = row.player_name if row.player_name in canonical_set \
            else raw_to_canonical.get(row.player_name)
        if target not in canonical_set:
            await db.delete(row)
            removed += 1
            continue
        current = preserved.get(target, {})
        preserved[target] = {
            "place": row.place if row.place is not None else current.get("place"),
            "points": row.points if row.points is not None else current.get("points"),
            "troop_level": row.troop_level if row.troop_level is not None else current.get("troop_level"),
            "rank": row.rank if row.rank is not None else current.get("rank"),
            "source": "ocr" if row.source == "ocr" else current.get("source", row.source),
        }
        await db.delete(row)

    await db.flush()

    for name in canonical_names:
        data = preserved.get(name, {})
        db.add(AncientRoster(
            collector_id=collector.id, player_name=name,
            place=data.get("place"), points=data.get("points"),
            troop_level=data.get("troop_level"), rank=data.get("rank"),
            source=data.get("source", "chests"), manual_expires_at=None,
        ))

    await db.commit()
    return {"synced": len(canonical_names), "removed": removed}


class JoinPayload(BaseModel):
    code: str


@router.post("/join")
async def join_as_editor(payload: JoinPayload,
                         user: User = Depends(get_web_user),
                         db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    invite = (await db.execute(
        select(AncientInviteCode).where(AncientInviteCode.code == payload.code)
    )).scalar_one_or_none()
    if not invite or invite.used_at is not None or invite.expires_at < now:
        raise HTTPException(status_code=404, detail="Invite code is invalid or expired")

    existing = (await db.execute(
        select(AncientEditor).where(
            AncientEditor.collector_id == invite.collector_id,
            AncientEditor.user_id == user.id,
        )
    )).scalar_one_or_none()
    if existing:
        existing.expires_at = now + timedelta(days=30)
    else:
        db.add(AncientEditor(
            collector_id=invite.collector_id,
            user_id=user.id,
            expires_at=now + timedelta(days=30),
        ))

    invite.used_at = now
    invite.used_by_user_id = user.id
    await db.commit()
    return {"ok": True}


@router.post("/{slug}/invite")
async def create_invite(slug: str,
                        user: User = Depends(get_web_user),
                        db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    now = datetime.now(timezone.utc)
    code = secrets.token_urlsafe(24)
    db.add(AncientInviteCode(
        collector_id=collector.id,
        code=code,
        expires_at=now + timedelta(hours=24),
    ))
    await db.commit()
    return {"code": code}
