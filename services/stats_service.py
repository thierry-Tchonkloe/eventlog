"""
services/stats_service.py
-------------------------
Les statistiques globales (spec §6).

"""

import aiosqlite
from models import StatsResponse


async def get_stats(db: aiosqlite.Connection) -> StatsResponse:
    # Total et répartition par kind
    async with db.execute("SELECT COUNT(*) as total FROM events") as cur:
        total = (await cur.fetchone())["total"]

    async with db.execute(
        "SELECT kind, COUNT(*) as cnt FROM events GROUP BY kind"
    ) as cur:
        rows = await cur.fetchall()
    events_by_kind = {row["kind"]: row["cnt"] for row in rows}

    # Unique users
    async with db.execute("SELECT COUNT(DISTINCT user_id) as u FROM events") as cur:
        unique_users = (await cur.fetchone())["u"]

    # Médiane des gaps
    median_gap = await _compute_median_gap(db)

    return StatsResponse(
        total_events=total,
        events_by_kind=events_by_kind,
        median_gap_seconds=median_gap,
        unique_users=unique_users,
    )


async def _compute_median_gap(db: aiosqlite.Connection) -> float | None:

    query = """
        WITH ordered AS (
            SELECT
                occurred_at_utc,
                LAG(occurred_at_utc) OVER (ORDER BY occurred_at_utc ASC) AS prev_occ
            FROM events
        )
        SELECT
            CAST(
                (strftime('%s', occurred_at_utc) - strftime('%s', prev_occ))
                AS REAL
            ) AS gap_seconds
        FROM ordered
        WHERE prev_occ IS NOT NULL
    """
    async with db.execute(query) as cur:
        rows = await cur.fetchall()

    gaps = [row["gap_seconds"] for row in rows if row["gap_seconds"] is not None]

    if len(gaps) < 1:
        # Moins de 2 événements → pas de gap possible (spec §6)
        return None

    return _median(gaps)


def _median(values: list[float]) -> float:

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0