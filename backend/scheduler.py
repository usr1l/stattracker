"""Background scheduler for market polling and data refresh jobs."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from market.futures import fetch_and_store_futures
from market.line_movement import detect_surges
from market.odds import poll_and_store_odds
from prediction.props_etl import refresh_all_props_data
from prediction.team_stats import refresh_team_stats

_scheduler: BackgroundScheduler = None


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
    _scheduler = scheduler
    return _scheduler


def start_scheduler() -> BackgroundScheduler:
    """Start scheduler if not already running."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
    return scheduler
