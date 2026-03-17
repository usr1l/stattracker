"""Standalone APScheduler worker process."""
from time import sleep

from bootstrap import prepare_runtime

prepare_runtime()

from app.logger import get_logger
from scheduler import start_scheduler

logger = get_logger(__name__)


def main() -> None:
    """Run the scheduler in a long-lived worker process."""
    scheduler = start_scheduler()
    logger.info("Scheduler worker started with %s jobs registered.", len(scheduler.get_jobs()))

    try:
        while True:
            sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler worker interrupted; shutting down.")
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
