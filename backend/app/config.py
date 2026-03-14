"""Configuration. Seasons loaded from season module (computed on startup)."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Project root: backend/app/config.py -> backend -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Seasons: loaded from file (written by refresh_seasons at startup)
from season import load_seasons

CURRENT_SEASON, PREVIOUS_SEASONS = load_seasons()
os.environ["CURRENT_SEASON"] = CURRENT_SEASON  # For get_players.get_players_by_team

# Cache
INSTANCE_PATH = Path(__file__).resolve().parent.parent / "instance"
INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
CACHE_PATH = INSTANCE_PATH / "cache.db"
CACHE_TTL_PLAYERS_HOURS = int(os.environ.get("CACHE_TTL_PLAYERS_HOURS", "24"))
CACHE_TTL_GAMELOGS_HOURS = int(os.environ.get("CACHE_TTL_GAMELOGS_HOURS", "6"))

# Path to players CSV (project root)
PLAYERS_CSV_PATH = PROJECT_ROOT / "players_csv" / "nba_players.csv"
