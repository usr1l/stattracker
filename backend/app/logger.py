"""Application logging helpers."""
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from flask import Flask

from app.config import LOG_LEVEL, LOGS_PATH

LOGGER_NAME = "stattracker"
LOG_FILE = Path(LOGS_PATH) / "app.log"


def _resolve_level(level_name: Optional[str] = None) -> int:
    return getattr(logging, (level_name or LOG_LEVEL).upper(), logging.INFO)


def configure_logging(app: Optional[Flask] = None, level_name: Optional[str] = None) -> logging.Logger:
    """Configure a shared rotating logger and optionally attach it to a Flask app."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    level = _resolve_level(level_name)
    logger = logging.getLogger(LOGGER_NAME)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = TimedRotatingFileHandler(
            LOG_FILE,
            when="midnight",
            interval=1,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.propagate = False

    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

    if app is not None:
        app.logger.handlers.clear()
        for handler in logger.handlers:
            app.logger.addHandler(handler)
        app.logger.setLevel(level)
        app.logger.propagate = False

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a child logger under the shared application logger namespace."""
    configure_logging()
    if not name or name == "__main__":
        return logging.getLogger(LOGGER_NAME)
    normalized = str(name).replace("/", ".")
    return logging.getLogger(f"{LOGGER_NAME}.{normalized}")
