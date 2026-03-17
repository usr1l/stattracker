"""Feature engineering pipeline for consolidated prediction models."""
from typing import Any, Dict, List, Mapping

from prediction.elo import get_team_elo, load_elo
from prediction.injuries import get_injury_summary
from prediction.referees import get_referee_bias
from prediction.schedule import get_schedule_context
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
    "home_distance_traveled",
    "away_distance_traveled",
]
CONTEXT_FEATURES = [
    "ref_home_bias",
    "ref_total_bias",
    "ref_foul_bias",
    "home_injury_impact",
    "away_injury_impact",
]
FEATURE_SNAPSHOT_GROUPS = {
    "elo": ELO_FEATURES,
    "stats": STATS_FEATURES,
    "schedule": SCHEDULE_FEATURES,
    "context": CONTEXT_FEATURES,
}
CONSOLIDATED_FEATURES = [
    *ELO_FEATURES,
    *STATS_FEATURES,
    *SCHEDULE_FEATURES,
    *CONTEXT_FEATURES,
]


def build_feature_row(
    features: Mapping[str, Any],
    feature_names: List[str] = None,
) -> List[float]:
    """Return a model-ready consolidated feature row."""
    names = feature_names or CONSOLIDATED_FEATURES
    return [float(features.get(name, 0.0) or 0.0) for name in names]


def build_feature_snapshot(
    home_team: str,
    away_team: str,
    game_date: str,
    game_id: str = None,
) -> Dict[str, Any]:
    """
    Build a nested snapshot of all feature groups for one game.
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

    # 3) Schedule and travel features
    schedule_context = get_schedule_context(home_abbr, away_abbr, game_date)

    # 4) Context features (referees + injuries)
    referee_bias = get_referee_bias(game_id)
    injury_summary = get_injury_summary(home_abbr, away_abbr, game_date)

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
        "schedule": schedule_context,
        "context": {
            "ref_home_bias": referee_bias["ref_home_bias"],
            "ref_total_bias": referee_bias["ref_total_bias"],
            "ref_foul_bias": referee_bias["ref_foul_bias"],
            "home_injury_impact": injury_summary["home_injury_impact"],
            "away_injury_impact": injury_summary["away_injury_impact"],
            "assigned_referees": referee_bias["assigned_referees"],
            "home_inactive_count": injury_summary["home_inactive_count"],
            "away_inactive_count": injury_summary["away_inactive_count"],
            "home_inactive_players": injury_summary["home_inactive_players"],
            "away_inactive_players": injury_summary["away_inactive_players"],
        },
    }


def flatten_feature_snapshot(snapshot: Mapping[str, Mapping[str, Any]]) -> Dict[str, float]:
    """Flatten grouped features into one consolidated numeric dictionary."""
    flattened: Dict[str, float] = {}
    for group, feature_names in FEATURE_SNAPSHOT_GROUPS.items():
        group_values = snapshot.get(group, {})
        for feature_name in feature_names:
            flattened[feature_name] = float(group_values.get(feature_name, 0.0) or 0.0)
    return flattened


def build_game_features(
    home_team: str,
    away_team: str,
    game_date: str,
    game_id: str = None,
) -> Dict[str, float]:
    """Build a consolidated flat feature vector for a specific upcoming game."""
    snapshot = build_feature_snapshot(
        home_team=home_team,
        away_team=away_team,
        game_date=game_date,
        game_id=game_id,
    )
    return flatten_feature_snapshot(snapshot)
