"""Configuration loaded from .env at project root."""
import os
import ast
from pathlib import Path

from dotenv import load_dotenv

# Project root: backend/app/config.py -> backend -> project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

CURRENT_SEASON = os.environ.get("CURRENT_SEASON", "2025-26")
os.environ["CURRENT_SEASON"] = CURRENT_SEASON  # Ensure get_players uses our config
_PREVIOUS_SEASONS_STR = os.environ.get("PREVIOUS_SEASONS", "['2025-26', '2024-25', '2023-24', '2022-23', '2021-22']")
try:
    PREVIOUS_SEASONS = ast.literal_eval(_PREVIOUS_SEASONS_STR)
except (ValueError, SyntaxError):
    PREVIOUS_SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23", "2021-22"]

# Cache
INSTANCE_PATH = Path(__file__).resolve().parent.parent / "instance"
INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
CACHE_PATH = INSTANCE_PATH / "cache.db"
CACHE_TTL_PLAYERS_HOURS = int(os.environ.get("CACHE_TTL_PLAYERS_HOURS", "24"))
CACHE_TTL_GAMELOGS_HOURS = int(os.environ.get("CACHE_TTL_GAMELOGS_HOURS", "6"))

# Path to players CSV (project root)
PLAYERS_CSV_PATH = PROJECT_ROOT / "players_csv" / "nba_players.csv"
