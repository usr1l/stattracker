"""Feature engineering pipeline for prediction models."""
from typing import Any, Dict, List

from prediction.elo import get_team_elo, load_elo
from prediction.schedule import get_rest_days
from prediction.team_stats import get_team_rolling_stats

ELO_FEATURES = ["elo_diff"]
STATS_FEATURES = [
    "net_rating_diff",
    "home_net_rating_l10",
    "away_net_rating_l10",
    "home_pace_l10",
    "away_pace_l10",
]
SCHEDULE_FEATURES = [
    "home_rest_days",
    "away_rest_days",
    "home_b2b",
    "away_b2b",
]

FEATURE_GROUPS = {
    "elo": ELO_FEATURES,
    "stats": STATS_FEATURES,
    "schedule": SCHEDULE_FEATURES,
}


def build_feature_row(features: Dict[str, Dict[str, Any]], group: str) -> List[float]:
    """Return a model-ready feature row for one feature subset."""
    return [float(features[group][name]) for name in FEATURE_GROUPS[group]]


def build_game_features(home_team: str, away_team: str, game_date: str) -> Dict[str, Any]:
    """
    Build a feature vector for a specific upcoming game.
    home_team/away_team: string abbreviations or full names matching ELO dict
    game_date: YYYY-MM-DD
    """
    # 1) ELO features
    ratings = load_elo()
    home_abbr = home_team.upper()
    away_abbr = away_team.upper()
    home_elo = get_team_elo(home_abbr, ratings)
    away_elo = get_team_elo(away_abbr, ratings)
    elo_diff = (home_elo + 100.0) - away_elo

    # 2) Team rolling stats
    home_stats = get_team_rolling_stats(home_abbr, game_date, window=10)
    away_stats = get_team_rolling_stats(away_abbr, game_date, window=10)
    net_rating_diff = home_stats["net_rating"] - away_stats["net_rating"]

    # 3) Schedule features
    home_rest = get_rest_days(home_abbr, game_date)
    away_rest = get_rest_days(away_abbr, game_date)

    return {
        "elo": {
            "elo_diff": elo_diff,
        },
        "stats": {
            "net_rating_diff": net_rating_diff,
            "home_net_rating_l10": home_stats["net_rating"],
            "away_net_rating_l10": away_stats["net_rating"],
            "home_pace_l10": home_stats["pace"],
            "away_pace_l10": away_stats["pace"],
        },
        "schedule": {
            "home_rest_days": home_rest,
            "away_rest_days": away_rest,
            "home_b2b": 1 if home_rest <= 1 else 0,
            "away_b2b": 1 if away_rest <= 1 else 0,
        },
    }
