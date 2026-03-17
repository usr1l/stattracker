"""Entry point for the local Flask backend."""
import os
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from bootstrap import prepare_runtime

prepare_runtime()

from app import create_app
from app.logger import get_logger
from market.db import get_db
from prediction.elo_builder import build_elo_from_history
from prediction.injuries import calculate_team_injury_impact, fetch_daily_injury_report
from prediction.referees import refresh_daily_referee_assignments
from prediction.team_stats import refresh_team_stats
from scheduler import start_scheduler
from season import load_seasons

logger = get_logger(__name__)
EASTERN = ZoneInfo("America/New_York")
STARTUP_CATCHUP_STALE_HOURS = int(os.environ.get("STARTUP_CATCHUP_STALE_HOURS", "24"))


def _parse_sql_date(value: Optional[str]) -> Optional[date]:
    """Parse a YYYY-MM-DD string into a date."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _latest_table_date(table_name: str, column_name: str) -> Optional[date]:
    """Return the latest stored date from a SQLite table."""
    conn = get_db()
    try:
        row = conn.execute(
            f"SELECT MAX({column_name}) AS latest_value FROM {table_name}"
        ).fetchone()
    finally:
        conn.close()
    return _parse_sql_date(row["latest_value"] if row else None)


def _is_older_than_threshold(latest_date: Optional[date], now_est: datetime) -> bool:
    """Return True when stored data is older than the configured catch-up threshold."""
    if latest_date is None:
        return True
    latest_dt = datetime.combine(latest_date, time.min, tzinfo=EASTERN)
    return (now_est - latest_dt) > timedelta(hours=STARTUP_CATCHUP_STALE_HOURS)


def run_startup_catchup() -> None:
    """Refresh stale local state before the dev server starts."""
    now_est = datetime.now(EASTERN)
    today = now_est.date().isoformat()
    _, seasons = load_seasons()

    latest_game_log_date = _latest_table_date("team_game_logs", "game_date")
    latest_injury_date = _latest_table_date("daily_injuries", "date")
    force_catchup = os.environ.get("FORCE_STARTUP_CATCHUP", "0") == "1"
    should_refresh_logs = force_catchup or _is_older_than_threshold(latest_game_log_date, now_est)
    should_refresh_injuries = force_catchup or latest_injury_date != now_est.date()

    logger.info(
        "Startup catch-up check: latest_game_log=%s latest_injury=%s force=%s",
        latest_game_log_date,
        latest_injury_date,
        force_catchup,
    )

    if should_refresh_logs:
        try:
            inserted = refresh_team_stats(seasons)
            logger.info("Catch-up refreshed team stats; rows inserted=%s", inserted)
        except Exception as exc:
            logger.warning("Catch-up team stats refresh failed: %s", exc)

        try:
            ratings = build_elo_from_history(seasons)
            logger.info("Catch-up rebuilt ELO ratings for %s teams.", len(ratings))
        except Exception as exc:
            logger.warning("Catch-up ELO rebuild failed: %s", exc)

    if should_refresh_injuries:
        try:
            rows = fetch_daily_injury_report(today)
            logger.info("Catch-up refreshed daily injuries for %s; rows=%s", today, len(rows))
        except Exception as exc:
            logger.warning("Catch-up injury report refresh failed: %s", exc)

        try:
            impact = calculate_team_injury_impact(today)
            logger.info("Catch-up refreshed team injury impact: %s", impact)
        except Exception as exc:
            logger.warning("Catch-up injury impact refresh failed: %s", exc)

    try:
        referee_summary = refresh_daily_referee_assignments(today)
        logger.info("Catch-up refreshed referee assignments: %s", referee_summary)
    except Exception as exc:
        logger.warning("Catch-up referee refresh failed: %s", exc)


app = create_app()


def main() -> None:
    """Run local Flask app with startup catch-up and the in-process scheduler."""
    run_startup_catchup()

    if os.environ.get("START_LOCAL_SCHEDULER_ON_RUN", "1") == "1":
        start_scheduler()
        logger.info("Local scheduler enabled for run.py process.")

    app.run(debug=True, port=5000, use_reloader=False)


if __name__ == "__main__":
    main()
