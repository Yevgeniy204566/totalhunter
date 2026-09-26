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
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chest_history import build_history_list, build_history_detail
from chest_slug import clan_to_slug, public_url
from chest_summary import enrich_with_profiles, pivot_summary, query_summary_rows, quota_slots_of
from database import get_db
from models import (
    Chest, ChestCatalogReference, ChestCollector, ChestConfiguration, ChestLocalization,
    ChestSeasonHistory, ChestTypeAlias, ChestTypeCatalog, PlayerAlias, PlayerProfile, User,
)
from web_routes import get_web_user

router = APIRouter(prefix="/web/dashboard/chests", tags=["chest-dashboard"])

# Global ready-made point/preset templates. Maintained by hand (Claude, on request) —
# not editable through the UI. T9 mirrors clan 229/BERS's live working configuration
# as of 2026-06-22, used as the reference template. New tiers (T8, ...) are added here
# as new dict keys, no API/schema changes required.
_T5_T8 = [
    {"catalog_id": "Common Crypt 25",   "points": 15,  "is_in_pattern": True},
    {"catalog_id": "Cursed Citadel 25", "points": 25,  "is_in_pattern": True},
    {"catalog_id": "Elven Citadel 25",  "points": 25,  "is_in_pattern": True},
    {"catalog_id": "Elven Citadel 30",  "points": 40,  "is_in_pattern": True},
    {"catalog_id": "Epic Crypt 20",     "points": 25,  "is_in_pattern": True},
    {"catalog_id": "Epic Crypt 25",     "points": 45,  "is_in_pattern": True},
    {"catalog_id": "Epic Crypt 30",     "points": 80,  "is_in_pattern": True},
    {"catalog_id": "Epic Crypt 35",     "points": 135, "is_in_pattern": True},
    {"catalog_id": "Rare Crypt 25",     "points": 35,  "is_in_pattern": True},
    {"catalog_id": "Rare Crypt 30",     "points": 65,  "is_in_pattern": True},
]

CHEST_PRESETS = {
    "T5": _T5_T8,
    "T6": _T5_T8,
    "T7": _T5_T8,
    "T8": _T5_T8,
    "T9": [
        {"catalog_id": "Epic Crypt 35", "points": 135, "is_in_pattern": True},
        {"catalog_id": "Epic Crypt 30", "points": 80, "is_in_pattern": True},
        {"catalog_id": "Rare Crypt 30", "points": 65, "is_in_pattern": True},
        {"catalog_id": "Epic Shadow City", "points": 55, "is_in_pattern": True},
        {"catalog_id": "Epic Crypt 25", "points": 45, "is_in_pattern": True},
        {"catalog_id": "Dark Omens Chest", "points": 45, "is_in_pattern": True},
        {"catalog_id": "Epic Briareus", "points": 45, "is_in_pattern": True},
        {"catalog_id": "Epic Arachne", "points": 40, "is_in_pattern": True},
        {"catalog_id": "Elven Citadel 30", "points": 40, "is_in_pattern": True},
        {"catalog_id": "Yogwai", "points": 40, "is_in_pattern": True},
        {"catalog_id": "Epic Fire Hydra", "points": 30, "is_in_pattern": True},
        {"catalog_id": "Epic Basilisk", "points": 30, "is_in_pattern": True},
        {"catalog_id": "Epic Undead", "points": 25, "is_in_pattern": True},
        {"catalog_id": "Epic Chimera", "points": 20, "is_in_pattern": True},
        {"catalog_id": "Rare Crypt 25", "points": 20, "is_in_pattern": True},
        {"catalog_id": "Epic Hellforge", "points": 20, "is_in_pattern": True},
        {"catalog_id": "Common Crypt 25", "points": 5, "is_in_pattern": True},
        {"catalog_id": "Epic Jormungander", "points": 5, "is_in_pattern": True},
        {"catalog_id": "Epic Fenrir", "points": 5, "is_in_pattern": True},
    ],
}


async def _load_known_catalog_ids(db: AsyncSession) -> set:
    reference_ids = (await db.execute(select(ChestCatalogReference.catalog_id))).scalars().all()
    catalog_ids = (await db.execute(select(ChestTypeCatalog.canonical_type))).scalars().all()
    localization_ids = (await db.execute(select(ChestLocalization.canonical_type))).scalars().all()
    return set(reference_ids) | set(catalog_ids) | set(localization_ids)


async def _load_catalog_options(db: AsyncSession) -> list:
    known_ids = sorted(await _load_known_catalog_ids(db))
    return [{"catalog_id": cid, "label": cid} for cid in known_ids]


@router.get("/presets")
async def get_presets(user: User = Depends(get_web_user)):
    return CHEST_PRESETS


@router.get("/my-custom-names")
async def get_my_custom_names(user: User = Depends(get_web_user),
                              db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(ChestTypeAlias.custom_name)
        .join(ChestCollector, ChestCollector.id == ChestTypeAlias.collector_id)
        .where(
            ChestCollector.user_id == user.id,
            ChestTypeAlias.custom_name.isnot(None),
            ChestTypeAlias.custom_name != "",
        )
        .distinct()
        .order_by(ChestTypeAlias.custom_name)
    )).scalars().all()
    return {"names": rows}


async def _raw_type_counts(db: AsyncSession, collector_id: int) -> dict:
    rows = (await db.execute(
        select(Chest.chest_type_raw, func.count())
        .where(Chest.collector_id == collector_id)
        .group_by(Chest.chest_type_raw)
    )).all()
    return {raw: count for raw, count in rows}


def _total_ever_for_catalog(catalog_id: Optional[str], aliases: list, raw_counts: dict) -> int:
    if catalog_id is None:
        return 0
    return sum(raw_counts.get(a.raw_type, 0) for a in aliases if a.catalog_id == catalog_id)


async def _load_localization_lookup(db: AsyncSession) -> dict:
    """display_text (нормализованный) -> canonical_type — глобальная таблица переводов
    (не per-collector), источник авто-сопоставления нераспознанных названий (владелец
    2026-09-25: пресет и реально увиденные в игре сундуки не объединялись — пресет
    матчился только по catalog_id, а у нераспознанных строк catalog_id всегда пуст)."""
    rows = (await db.execute(select(ChestLocalization.display_text, ChestLocalization.canonical_type))).all()
    return {text.strip().lower(): canonical for text, canonical in rows}


async def _collector_rows(db: AsyncSession, collector: ChestCollector) -> list:
    aliases = (await db.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalars().all()
    configs = (await db.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalars().all()
    config_by_catalog_id = {c.catalog_id: c for c in configs}
    raw_counts = await _raw_type_counts(db, collector.id)
    localization_lookup = await _load_localization_lookup(db)

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
            "quota_slot": config.quota_slot if config else None,
            "total_ever": _total_ever_for_catalog(alias.catalog_id, aliases, raw_counts),
        })

    # Авто-сопоставление нераспознанных строк (владелец 2026-09-25: загруженный пресет и
    # реально увиденные ботом сундуки не объединялись — пресет матчился только по
    # catalog_id, а у нераспознанных строк catalog_id всегда пуст). Точное совпадение
    # (без учёта регистра/пробелов по краям) с уже известным переводом эталонного типа
    # (_load_localization_lookup) — без внешнего переводчика, только локальная таблица.
    # ДО цикла по "осиротевшим" конфигурациям ниже: иначе конфигурация без алиаса и
    # только что найденная авто-связанная строка задвоились бы на один catalog_id.
    # Ничего не пишем в БД здесь (это GET) — реальную связь (alias) создаёт, как обычно,
    # «Сохранить» (POST /rows), когда в строке уже проставлен catalog_id.
    mapped_raw_types = {a.raw_type for a in aliases}
    unmapped = (await db.execute(
        select(Chest.chest_type_raw).distinct()
        .where(Chest.collector_id == collector.id)
    )).scalars().all()
    for raw_type in unmapped:
        if raw_type in mapped_raw_types:
            continue
        matched_catalog_id = localization_lookup.get(raw_type.strip().lower()) if raw_type else None
        if matched_catalog_id:
            config = config_by_catalog_id.get(matched_catalog_id)
            seen_catalog_ids.add(matched_catalog_id)
            rows.append({
                "raw_type": raw_type, "catalog_id": matched_catalog_id,
                "custom_name": config.custom_name if config else None,
                "points": config.points if config else 0,
                "is_in_pattern": config.is_in_pattern if config else False,
                "quota_slot": config.quota_slot if config else None,
                "total_ever": raw_counts.get(raw_type, 0),
            })
        else:
            rows.append({"raw_type": raw_type, "catalog_id": None, "custom_name": None,
                         "points": 0, "is_in_pattern": False, "quota_slot": None,
                         "total_ever": raw_counts.get(raw_type, 0)})

    for config in configs:
        if config.catalog_id in seen_catalog_ids:
            continue
        rows.append({
            "raw_type": None, "catalog_id": config.catalog_id,
            "custom_name": config.custom_name, "points": config.points,
            "is_in_pattern": config.is_in_pattern,
            "quota_slot": config.quota_slot,
            "total_ever": _total_ever_for_catalog(config.catalog_id, aliases, raw_counts),
        })

    return rows


async def _player_alias_rows(db: AsyncSession, collector: ChestCollector,
                             global_alias_map: dict | None = None) -> list:
    aliases = (await db.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()

    profiles = (await db.execute(
        select(PlayerProfile).where(PlayerProfile.collector_id == collector.id)
    )).scalars().all()
    profile_map = {p.canonical_name: p for p in profiles}

    rows = []
    for a in aliases:
        profile = profile_map.get(a.canonical_name)
        rows.append({
            "raw_name": a.raw_name,
            "canonical_name": a.canonical_name,
            "rank": profile.rank if profile else None,
            "troop_level": profile.troop_level if profile else None,
            "hero_level": profile.hero_level if profile else None,
        })

    mapped_raw_names = {a.raw_name for a in aliases}
    unmapped = (await db.execute(
        select(Chest.sender_raw).distinct()
        .where(Chest.collector_id == collector.id)
    )).scalars().all()
    for raw_name in unmapped:
        if raw_name in mapped_raw_names:
            continue
        canonical = (global_alias_map or {}).get(raw_name)
        profile = profile_map.get(canonical or raw_name)
        rows.append({
            "raw_name": raw_name,
            "canonical_name": canonical or raw_name,  # fallback so POST can always save
            "rank": profile.rank if profile else None,
            "troop_level": profile.troop_level if profile else None,
            "hero_level": profile.hero_level if profile else None,
        })

    return rows


@router.get("")
async def get_dashboard_chests(user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    last_chest_sub = (
        select(Chest.collector_id, func.max(Chest.created_at).label("last_chest"))
        .group_by(Chest.collector_id)
        .subquery()
    )
    collectors = (await db.execute(
        select(ChestCollector)
        .outerjoin(last_chest_sub, ChestCollector.id == last_chest_sub.c.collector_id)
        .where(ChestCollector.user_id == user.id)
        .order_by(last_chest_sub.c.last_chest.desc().nulls_last())
    )).scalars().all()

    global_alias_rows = (await db.execute(
        select(PlayerAlias.raw_name, PlayerAlias.canonical_name)
        .join(ChestCollector, ChestCollector.id == PlayerAlias.collector_id)
        .where(
            ChestCollector.user_id == user.id,
            PlayerAlias.canonical_name.isnot(None),
            PlayerAlias.canonical_name != "",
        )
        .order_by(PlayerAlias.id)
    )).all()
    global_alias_map = {r.raw_name: r.canonical_name for r in global_alias_rows}

    result = []
    for collector in collectors:
        # Регрессия владельца 2026-09-25: клан на кириллице ("Феникс") давал ПУСТОЙ слаг
        # (/c/229/ без хвоста) — clan_to_slug теперь транслитерирует. Владелец явно
        # потребовал: ОСНОВНАЯ публичная ссылка (public_url, кнопка «🔗») должна САМА
        # быть в красивом виде /c/{kingdom}/{slug}, а не мелкой второй ссылкой снизу.
        # Для языков вне таблицы транслитерации (иероглифы и т.п.) слаг всё ещё может
        # быть пустым — тогда откатываемся на старую (гарантированно рабочую) ссылку
        # по случайному slug, вместо битой /c/{kingdom}/ с пустым хвостом.
        _raw_url = f"https://total-hunter.com/chests/{collector.slug}"
        _public = public_url(collector.kingdom, collector.clan, collector.custom_slug, collector.slug)
        _nice_url = _public if _public != _raw_url else None
        result.append({
            "slug": collector.slug, "kingdom": collector.kingdom, "clan": collector.clan,
            "language": collector.language,
            "public_url": _nice_url or _raw_url,
            "short_url": _raw_url if _nice_url else None,
            "rows": await _collector_rows(db, collector),
            "player_alias_rows": await _player_alias_rows(db, collector, global_alias_map),
            "catalog_options": await _load_catalog_options(db),
            "timezone_offset_minutes": collector.timezone_offset_minutes,
            "period_start": collector.period_start,
            "period_end": collector.period_end,
            "target_points": collector.target_points,
            "target_chests": collector.target_chests,
            "quotas": collector.quotas or [],
            "leader_canonical_name": collector.leader_canonical_name,
            "leader_excluded_catalog_ids": collector.leader_excluded_catalog_ids or [],
        })
    return {"collectors": result}


class RowIn(BaseModel):
    raw_type: Optional[str] = None
    catalog_id: Optional[str] = None
    custom_name: Optional[str] = None
    points: int = 0
    is_in_pattern: bool = False
    counts_toward_quota: bool = False   # устарело (старый сайт в окне деплоя) — игнорируется
    quota_slot: Optional[int] = Field(default=None, ge=1, le=3)


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

    seen_catalog_ids = set()
    for row in payload.rows:
        if row.raw_type is not None and row.catalog_id is not None:
            db.add(ChestTypeAlias(collector_id=collector.id, raw_type=row.raw_type,
                                  catalog_id=row.catalog_id))

        if row.catalog_id is not None and row.catalog_id not in seen_catalog_ids:
            seen_catalog_ids.add(row.catalog_id)
            db.add(ChestConfiguration(collector_id=collector.id, catalog_id=row.catalog_id,
                                      custom_name=row.custom_name, points=row.points,
                                      # квота ⇒ в учёте (CHECK ck_chest_config_slot_in_account)
                                      is_in_pattern=row.is_in_pattern or row.quota_slot is not None,
                                      quota_slot=row.quota_slot))

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


class PlayerProfileRowIn(BaseModel):
    canonical_name: str
    rank: Optional[str] = None
    troop_level: Optional[str] = None
    # Кабинет сохраняет профили целиком (delete+insert) — поле обязано приходить, иначе затрётся.
    hero_level: Optional[int] = Field(default=None, ge=1, le=999)


class PlayerProfilesPayload(BaseModel):
    collector_slug: str
    rows: List[PlayerProfileRowIn] = []


@router.post("/player-profiles")
async def post_player_profiles(payload: PlayerProfilesPayload,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, payload.collector_slug, user)

    await db.execute(delete(PlayerProfile).where(PlayerProfile.collector_id == collector.id))

    seen: set[str] = set()
    for row in payload.rows:
        canonical = (row.canonical_name or "").strip()
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        db.add(PlayerProfile(
            collector_id=collector.id,
            canonical_name=canonical,
            rank=row.rank or None,
            troop_level=row.troop_level or None,
            hero_level=row.hero_level,
        ))

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


class QuotaIn(BaseModel):
    slot: int = Field(ge=1, le=3)
    name: str = Field(min_length=1, max_length=40)
    target: Optional[int] = Field(default=None, ge=0)
    # fixed — одна цель на всех; per_player — личная цель по уровню Героя (спека 02),
    # все коэффициенты правит лидер: формула будет уточняться по статистике.
    mode: Literal["fixed", "per_player"] = "fixed"
    hero_k: float = Field(default=0, ge=-100, le=100)     # % цели на 100 уровней Героя
    hero_h0: int = Field(default=400, ge=1, le=999)       # «средний» уровень Героя


class SeasonSettingsPayload(BaseModel):
    timezone_offset_minutes: Optional[int] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    target_points: Optional[int] = None
    target_chests: Optional[int] = None
    quotas: Optional[List[QuotaIn]] = Field(default=None, max_length=3)

    @field_validator("quotas")
    @classmethod
    def _unique_slots(cls, v):
        if v is not None and len({q.slot for q in v}) != len(v):
            raise ValueError("duplicate quota slot")
        return v


class LeaderSettingsPayload(BaseModel):
    leader_canonical_name: Optional[str] = None
    leader_excluded_catalog_ids: List[str] = []


@router.patch("/{slug}/leader")
async def update_leader_settings(slug: str, payload: LeaderSettingsPayload,
                                  user: User = Depends(get_web_user),
                                  db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    if payload.leader_canonical_name is not None:
        # Validate name exists: check PlayerAlias first, then raw sender_canonical
        alias_hit = (await db.execute(
            select(PlayerAlias.canonical_name)
            .where(PlayerAlias.collector_id == collector.id,
                   PlayerAlias.canonical_name == payload.leader_canonical_name)
        )).scalar_one_or_none()
        sender_hit = None
        if alias_hit is None:
            sender_hit = (await db.execute(
                select(Chest.sender_canonical)
                .where(Chest.collector_id == collector.id,
                       Chest.sender_canonical == payload.leader_canonical_name)
                .limit(1)
            )).scalar_one_or_none()
        if alias_hit is None and sender_hit is None:
            raise HTTPException(status_code=400, detail="Unknown player")
    collector.leader_canonical_name = payload.leader_canonical_name
    collector.leader_excluded_catalog_ids = payload.leader_excluded_catalog_ids
    await db.commit()
    return {"ok": True}


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
    if payload.quotas is not None:
        # коэффициенты храним только у персональных квот — у fixed они ни на что не влияют
        collector.quotas = [
            q.model_dump() if q.mode == "per_player"
            else q.model_dump(include={"slot", "name", "target", "mode"})
            for q in sorted(payload.quotas, key=lambda q: q.slot)
        ]
    if payload.period_start is not None or payload.period_end is not None:
        collector.stopped_at = None

    await db.commit()
    return {"ok": True}


@router.post("/{slug}/close-season")
async def close_season_early(slug: str, user: User = Depends(get_web_user),
                              db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    if collector.period_start is None or collector.period_end is None:
        raise HTTPException(status_code=400, detail="No active season")

    now = datetime.utcnow()
    rows = await query_summary_rows(db, collector, collector.period_start, now)
    summary = pivot_summary(
        collector.kingdom, collector.clan, rows,
        leader_name=collector.leader_canonical_name,
        leader_excluded=frozenset(collector.leader_excluded_catalog_ids or []),
        quota_slots=quota_slots_of(collector.quotas),
    )
    await enrich_with_profiles(db, collector.id, summary, collector.quotas)

    db.add(ChestSeasonHistory(
        collector_id=collector.id,
        period_start=collector.period_start,
        period_end=now,
        target_points_snapshot=collector.target_points,
        target_chests_snapshot=collector.target_chests,
        quotas_snapshot=list(collector.quotas or []),
        summary_json=summary,
    ))
    await db.execute(
        delete(Chest).where(
            Chest.collector_id == collector.id,
            Chest.collected_at >= collector.period_start,
            Chest.collected_at <= now,
        )
    )
    collector.period_start = None
    collector.period_end = None
    collector.stopped_at = now
    await db.commit()
    return {"ok": True}


@router.delete("/{slug}")
async def delete_collector(slug: str, user: User = Depends(get_web_user),
                           db: AsyncSession = Depends(get_db)):
    from models import (
        AncientRoster, AncientNameMapping, AncientEditor, AncientInviteCode,
        AncientCalculation, ClanRosterEntry,
    )
    collector = await _get_own_collector(db, slug, user)
    # Cascades not guaranteed in all FK definitions — delete explicitly in order
    await db.execute(delete(Chest).where(Chest.collector_id == collector.id))
    await db.execute(delete(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id))
    await db.execute(delete(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id))
    await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == collector.id))
    await db.execute(delete(ClanRosterEntry).where(ClanRosterEntry.collector_id == collector.id))
    await db.execute(delete(PlayerProfile).where(PlayerProfile.collector_id == collector.id))
    await db.execute(delete(ChestSeasonHistory).where(ChestSeasonHistory.collector_id == collector.id))
    await db.execute(delete(AncientRoster).where(AncientRoster.collector_id == collector.id))
    await db.execute(delete(AncientCalculation).where(AncientCalculation.collector_id == collector.id))
    await db.execute(delete(AncientNameMapping).where(AncientNameMapping.collector_id == collector.id))
    await db.execute(delete(AncientEditor).where(AncientEditor.collector_id == collector.id))
    await db.execute(delete(AncientInviteCode).where(AncientInviteCode.collector_id == collector.id))
    await db.execute(delete(ChestCollector).where(ChestCollector.id == collector.id))
    await db.commit()
    return {"ok": True}


@router.get("/{slug}/stats.csv")
async def dashboard_stats_csv(slug: str, user: User = Depends(get_web_user),
                              db: AsyncSession = Depends(get_db)):
    """Статистика для подбора коэффициентов квоты EM (спека 02): по строке на игрока в каждом
    закрытом сезоне + текущем — войска G/S/M, Герой, очки, сундуки каждой квоты. Сезоны,
    закрытые до спеки 02, без войск/Героя (пусто) — не падают."""
    import csv
    import io
    from fastapi.responses import Response
    collector = await _get_own_collector(db, slug, user)

    seasons = (await db.execute(
        select(ChestSeasonHistory).where(ChestSeasonHistory.collector_id == collector.id)
        .order_by(ChestSeasonHistory.period_start)
    )).scalars().all()
    blocks = []
    for sn in seasons:
        quotas = sn.quotas_snapshot if sn.quotas_snapshot is not None else (
            [{"slot": 1, "name": "Epic Crypts"}])
        blocks.append((sn.period_start, sn.period_end, sn.summary_json.get("players", []), quotas))
    if collector.period_start is not None:
        rows = await query_summary_rows(db, collector, collector.period_start, collector.period_end)
        live = pivot_summary(collector.kingdom, collector.clan, rows,
                             leader_name=collector.leader_canonical_name,
                             leader_excluded=frozenset(collector.leader_excluded_catalog_ids or []),
                             quota_slots=quota_slots_of(collector.quotas))
        await enrich_with_profiles(db, collector.id, live, collector.quotas)
        blocks.append((collector.period_start, collector.period_end, live["players"], collector.quotas or []))

    quota_names = []
    for *_, quotas in blocks:
        for q in quotas:
            if q["name"] not in quota_names:
                quota_names.append(q["name"])

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["season_start", "season_end", "player", "G", "S", "M", "hero", "points", *quota_names])
    for start, end, players, quotas in blocks:
        slot_by_name = {q["name"]: str(q["slot"]) for q in quotas}
        for p in players:
            troop = p.get("troop_level") or ""
            gsm = [troop[1:2], troop[4:5], troop[7:8]] if troop else ["", "", ""]
            counts = p.get("quotas") or ({"1": p.get("quota_chests", 0)} if "quota_chests" in p else {})
            w.writerow([
                start.isoformat() if start else "", end.isoformat() if end else "", p["name"], *gsm,
                p.get("hero_level") or "", p.get("points", 0),
                *[counts.get(slot_by_name[n], "") if n in slot_by_name else "" for n in quota_names],
            ])
    # BOM — чтобы Excel сразу открыл кириллицу правильно
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="chests-stats-{collector.kingdom}.csv"'})


@router.get("/{slug}/history")
async def get_dashboard_history(slug: str, user: User = Depends(get_web_user),
                                db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    return {"seasons": await build_history_list(db, collector.id)}


@router.get("/{slug}/history/{season_id}")
async def get_dashboard_history_detail(slug: str, season_id: int,
                                       user: User = Depends(get_web_user),
                                       db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    detail = await build_history_detail(db, collector.id, season_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Season not found")
    return detail
