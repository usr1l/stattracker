"""Background scheduler for market polling and data refresh jobs."""
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.logger import get_logger
from cleanup import cleanup_old_market_data
from live.client import are_games_currently_active, poll_live_games
from market.futures import fetch_and_store_futures
from market.line_movement import detect_surges
from market.odds import poll_and_store_odds
from prediction.injuries import calculate_team_injury_impact
from prediction.props_etl import refresh_all_props_data
from prediction.referees import refresh_daily_referee_assignments
from prediction.team_stats import refresh_team_stats

_scheduler: BackgroundScheduler = None
logger = get_logger(__name__)
EASTERN_TZ = ZoneInfo("America/New_York")


def poll_live_games_job() -> int:
    """Poll live games only while local NBA windows are active."""
    if not are_games_currently_active():
        logger.info("Skipping live polling job because there are no active NBA windows to track.")
        return 0
    return poll_live_games(skip_window_check=True)


def get_scheduler() -> BackgroundScheduler:
    """Create scheduler singleton and register jobs once."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        poll_and_store_odds,
        trigger=IntervalTrigger(minutes=15),
        id="poll_odds",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        poll_live_games_job,
        trigger=IntervalTrigger(minutes=3),
        id="poll_live_games",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        detect_surges,
        trigger=IntervalTrigger(minutes=15),
        id="detect_surges",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        refresh_team_stats,
        trigger=CronTrigger(hour=5, minute=0),
        id="refresh_team_stats",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        calculate_team_injury_impact,
        trigger=CronTrigger(hour=14, minute=0, timezone=EASTERN_TZ),
        id="refresh_team_injury_impact_2pm",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        calculate_team_injury_impact,
        trigger=CronTrigger(hour=17, minute=0, timezone=EASTERN_TZ),
        id="refresh_team_injury_impact_5pm",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        refresh_daily_referee_assignments,
        trigger=CronTrigger(hour=16, minute=10),
        id="refresh_daily_referees",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        refresh_all_props_data,
        trigger=CronTrigger(hour=5, minute=0),
        id="refresh_props_data",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        fetch_and_store_futures,
        trigger=CronTrigger(hour=6, minute=0),
        id="refresh_futures",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        cleanup_old_market_data,
        trigger=CronTrigger(day_of_week="sun", hour=7, minute=30),
        id="cleanup_market_data",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler = scheduler
    return _scheduler


def start_scheduler() -> BackgroundScheduler:
    """Start scheduler if not already running."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Background scheduler started with %s jobs.", len(scheduler.get_jobs()))
    return scheduler
