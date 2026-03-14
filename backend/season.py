"""Season computation and persistence. NBA season: Oct–May in progress, Jun–Sep offseason."""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

# backend/season.py - instance is backend/instance/
INSTANCE_PATH = Path(__file__).resolve().parent / "instance"
SEASONS_FILE = INSTANCE_PATH / "seasons.json"


def compute_current_season() -> str:
    """
    Compute current NBA season from date.
    Oct–Dec: season just started. Jan–May: season ongoing. Jun–Sep: offseason (most recent).
    """
    now = datetime.now()
    year, month = now.year, now.month
    if month >= 10:
        start_year = year
    elif month <= 5:
        start_year = year - 1
    else:
        start_year = year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def compute_seasons(count: int = 10) -> List[str]:
    """Build list of seasons: current + (count-1) previous."""
    current = compute_current_season()
    start_year = int(current.split("-")[0])
    return [f"{s}-{str(s + 1)[-2:]}" for s in range(start_year, start_year - count, -1)]


def load_seasons() -> Tuple[str, List[str]]:
    """Read seasons from file. If missing, compute and save."""
    INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
    if SEASONS_FILE.exists():
        data = json.loads(SEASONS_FILE.read_text())
        return data["current_season"], data["seasons"]
    return refresh_seasons()


def refresh_seasons() -> Tuple[str, List[str]]:
    """Compute seasons, save to file, return (current, seasons)."""
    INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
    current = compute_current_season()
    seasons = compute_seasons(10)
    SEASONS_FILE.write_text(
        json.dumps({"current_season": current, "seasons": seasons}, indent=2)
    )
    return current, seasons
