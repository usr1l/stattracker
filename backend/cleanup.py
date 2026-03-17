"""Data retention helpers for market history tables."""
import os
from datetime import datetime, timedelta

from app.logger import get_logger
from market.db import get_db

logger = get_logger(__name__)
DEFAULT_RETENTION_DAYS = int(os.environ.get("ODDS_HISTORY_RETENTION_DAYS", "7"))


def cleanup_old_market_data(retention_days: int = DEFAULT_RETENTION_DAYS) -> dict:
    """Delete stale minute-by-minute odds rows while preserving opening and closing snapshots."""
    cutoff = (datetime.utcnow() - timedelta(days=int(retention_days))).strftime("%Y-%m-%d %H:%M:%S")
    deleted_odds_rows = 0

    conn = get_db()
    try:
        completed_games = conn.execute(
            """
            SELECT DISTINCT game_id
            FROM odds_history
            WHERE commence_time < ?
            """,
            (cutoff,),
        ).fetchall()

        for row in completed_games:
            game_id = row["game_id"]
            market_rows = conn.execute(
                """
                SELECT DISTINCT market_type
                FROM odds_history
                WHERE game_id = ?
                """,
                (game_id,),
            ).fetchall()

            for market in market_rows:
                market_type = market["market_type"]
                oldest = conn.execute(
                    """
                    SELECT id
                    FROM odds_history
                    WHERE game_id = ? AND market_type = ?
                    ORDER BY timestamp ASC
                    LIMIT 1
                    """,
                    (game_id, market_type),
                ).fetchone()
                newest = conn.execute(
                    """
                    SELECT id
                    FROM odds_history
                    WHERE game_id = ? AND market_type = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (game_id, market_type),
                ).fetchone()

                keep_ids = {
                    record["id"]
                    for record in (oldest, newest)
                    if record is not None and record["id"] is not None
                }

                sql = """
                    DELETE FROM odds_history
                    WHERE game_id = ? AND market_type = ? AND commence_time < ?
                """
                params = [game_id, market_type, cutoff]
                if keep_ids:
                    placeholders = ",".join("?" for _ in keep_ids)
                    sql += f" AND id NOT IN ({placeholders})"
                    params.extend(sorted(keep_ids))

                cursor = conn.execute(sql, tuple(params))
                deleted_odds_rows += cursor.rowcount

        deleted_live_rows = conn.execute(
            """
            DELETE FROM live_game_state
            WHERE COALESCE(seconds_remaining, 0) <= 0 OR last_updated < ?
            """,
            (cutoff,),
        ).rowcount

        conn.commit()
    finally:
        conn.close()

    result = {
        "cutoff": cutoff,
        "deleted_odds_rows": deleted_odds_rows,
        "deleted_live_rows": deleted_live_rows,
    }
    logger.info("Market data cleanup complete: %s", result)
    return result


if __name__ == "__main__":
    from bootstrap import prepare_runtime

    prepare_runtime(fetch_players=False)
    cleanup_old_market_data()
