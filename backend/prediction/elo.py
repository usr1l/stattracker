"""ELO Rating System for NBA teams."""
import json
import math
from pathlib import Path
from typing import Dict

# Paths
INSTANCE_PATH = Path(__file__).resolve().parent.parent / "instance"
ELO_FILE = INSTANCE_PATH / "elo.json"

# Constants
INITIAL_ELO = 1500.0
K_FACTOR = 20.0
HOME_ADVANTAGE = 100.0
MEAN_REVERSION = 0.33


def load_elo() -> Dict[str, float]:
    """Load ELO ratings from disk. Returns empty dict if missing."""
    if ELO_FILE.exists():
        try:
            return json.loads(ELO_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_elo(ratings: Dict[str, float]) -> None:
    """Persist ELO ratings to disk."""
    INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
    ELO_FILE.write_text(json.dumps(ratings, indent=2))


def get_team_elo(team: str, ratings: Dict[str, float]) -> float:
    """Get current ELO for a team, initializing if needed."""
    return ratings.get(team, INITIAL_ELO)


def get_expected_win_prob(elo_diff: float) -> float:
    """Calculate expected win probability for the home team given ELO diff."""
    # diff = (home_elo + home_adv) - away_elo
    return 1.0 / (1.0 + math.pow(10, -elo_diff / 400.0))


def apply_season_carryover(ratings: Dict[str, float]) -> Dict[str, float]:
    """Regress all ELO ratings toward the mean (1500) for a new season."""
    new_ratings = {}
    for team, elo in ratings.items():
        new_ratings[team] = (elo * (1 - MEAN_REVERSION)) + (INITIAL_ELO * MEAN_REVERSION)
    return new_ratings


def update_elo_post_game(
    home_team: str, away_team: str, home_score: int, away_score: int, ratings: Dict[str, float]
) -> None:
    """
    Update ELO ratings in-place after a game result.
    If the game goes to OT or has extreme margins, K could be scaled by margin of victory,
    but standard 20 is used here as a baseline.
    """
    home_elo = get_team_elo(home_team, ratings)
    away_elo = get_team_elo(away_team, ratings)
    
    # Adjust for home court
    elo_diff = (home_elo + HOME_ADVANTAGE) - away_elo
    
    expected_home = get_expected_win_prob(elo_diff)
    
    # 1 if home won, 0 if away won
    home_result = 1.0 if home_score > away_score else 0.0
    
    # Standard update
    shift = K_FACTOR * (home_result - expected_home)
    
    ratings[home_team] = home_elo + shift
    ratings[away_team] = away_elo - shift
