"""
chest_summary.py — shared pivot/query logic for chest summaries.

Used by both the live GET /chests/summary/{slug} endpoint (chests.py) and the
season archiver (chest_history.py). Lives in its own module — neither of those
two may import from the other without creating a circular import, since
chests.py needs chest_history.py's history endpoints helpers and
chest_history.py needs this module's summary-building logic.
"""
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Chest, ChestConfiguration, ChestCollector, ChestLocalization, ChestTypeAlias, PlayerAlias


def pivot_summary(kingdom: str, clan: str, rows, *,
                  leader_name: str | None = None,
                  leader_excluded: frozenset = frozenset()) -> dict:
    """rows: iterable of (sender, chest_type_en, display_name, points_per_unit,
    counts_toward_quota, count).

    chest_type_en is used as the internal dedup/grouping key (stable, language-
    independent) — display_name is only substituted in at the very end, so two
    different chest types that happen to share an identical translation can never be
    merged into one row by mistake.

    leader_name / leader_excluded: when a collector marks certain catalog IDs as
    excluded for the clan leader, those chest types still count toward clan totals
    and grand_total (the raw numbers are real) but are stripped from the leader's
    per_player row and point tally so they don't distort the ranking table.
    """
    chest_type_order: list[str] = []
    seen_types = set()
    display_names: dict[str, str] = {}
    per_player: dict[str, dict[str, int]] = {}
    player_points: dict[str, int] = {}
    player_quota: dict[str, int] = {}
    totals: dict[str, int] = {}
    grand_total = 0
    total_points = 0

    for sender, chest_type_en, display_name, points, counts_toward_quota, count in rows:
        if leader_name and sender == leader_name and chest_type_en in leader_excluded:
            # Excluded from leader score but still tracked in clan totals
            grand_total += count
            totals[chest_type_en] = totals.get(chest_type_en, 0) + count
            if chest_type_en not in seen_types:
                seen_types.add(chest_type_en)
                chest_type_order.append(chest_type_en)
                display_names[chest_type_en] = display_name
            continue
        if chest_type_en not in seen_types:
            seen_types.add(chest_type_en)
            chest_type_order.append(chest_type_en)
            display_names[chest_type_en] = display_name
        per_player.setdefault(sender, {})
        per_player[sender][chest_type_en] = per_player[sender].get(chest_type_en, 0) + count
        player_points[sender] = player_points.get(sender, 0) + count * points
        if counts_toward_quota:
            player_quota[sender] = player_quota.get(sender, 0) + count
        totals[chest_type_en] = totals.get(chest_type_en, 0) + count
        grand_total += count
        total_points += count * points

    chest_type_order_sorted = sorted(
        seen_types, key=lambda t: (-totals[t], display_names[t])
    )
    chest_types = [display_names[t] for t in chest_type_order_sorted]
    players = []
    for sender, counts_by_en in per_player.items():
        counts = {display_names[t]: c for t, c in counts_by_en.items()}
        players.append({
            "name": sender,
            "counts": counts,
            "total": sum(counts_by_en.values()),
            "points": player_points[sender],
            "quota_chests": player_quota.get(sender, 0),
        })
    players.sort(key=lambda p: (-p["points"], p["name"]))

    totals_out = {display_names[t]: c for t, c in totals.items()}
    totals_out["grand_total"] = grand_total
    totals_out["total_points"] = total_points

    return {
        "kingdom": kingdom,
        "clan": clan,
        "chest_types": chest_types,
        "players": players,
        "totals": totals_out,
    }


async def query_summary_rows(db: AsyncSession, collector: ChestCollector,
                             period_start, period_end):
    sender_expr = func.coalesce(PlayerAlias.canonical_name, Chest.sender_raw)
    chest_type_expr = func.coalesce(ChestTypeAlias.catalog_id, Chest.chest_type_raw)
    display_expr = func.coalesce(ChestConfiguration.custom_name,
                                 ChestLocalization.display_text, chest_type_expr)

    rows_query = (
        select(sender_expr, chest_type_expr, display_expr, ChestConfiguration.points,
               ChestConfiguration.counts_toward_quota, func.count())
        .select_from(Chest)
        .outerjoin(
            PlayerAlias,
            and_(PlayerAlias.collector_id == Chest.collector_id,
                 PlayerAlias.raw_name == Chest.sender_raw),
        )
        .outerjoin(
            ChestTypeAlias,
            and_(ChestTypeAlias.collector_id == Chest.collector_id,
                 ChestTypeAlias.raw_type == Chest.chest_type_raw),
        )
        .join(
            ChestConfiguration,
            and_(ChestConfiguration.collector_id == Chest.collector_id,
                 ChestConfiguration.catalog_id == chest_type_expr,
                 ChestConfiguration.is_in_pattern.is_(True)),
        )
        .outerjoin(
            ChestLocalization,
            and_(ChestLocalization.canonical_type == chest_type_expr,
                 ChestLocalization.language == collector.language),
        )
        .where(Chest.collector_id == collector.id)
    )
    if period_start is not None:
        rows_query = rows_query.where(Chest.collected_at >= period_start)
    if period_end is not None:
        rows_query = rows_query.where(Chest.collected_at <= period_end)

    rows_query = rows_query.group_by(sender_expr, chest_type_expr, display_expr,
                                     ChestConfiguration.points,
                                     ChestConfiguration.counts_toward_quota)
    return (await db.execute(rows_query)).all()
