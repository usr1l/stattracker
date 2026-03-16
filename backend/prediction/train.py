"""Historical training pipeline for ensemble prediction models."""
from typing import Dict, List, Optional, Tuple

import numpy as np

from market.db import get_db
from prediction.features import FEATURE_GROUPS, build_feature_row, build_game_features
from prediction.model import train_ensemble_models
from prediction.team_stats import refresh_team_stats
from season import load_seasons


def _load_training_games(seasons: List[str]) -> List[dict]:
    """Load historical completed games from team_game_logs."""
    conn = get_db()
    try:
        placeholders = ",".join("?" for _ in seasons)
        rows = conn.execute(
            f"""
            SELECT season, game_id, game_date, team_abbr, matchup, pts
            FROM team_game_logs
            WHERE season IN ({placeholders})
              AND pts IS NOT NULL
            ORDER BY game_date ASC, game_id ASC
            """,
            tuple(seasons),
        ).fetchall()
    finally:
        conn.close()

    by_game: Dict[str, List[dict]] = {}
    for row in rows:
        by_game.setdefault(row["game_id"], []).append(dict(row))

    games: List[dict] = []
    for game_id, team_rows in by_game.items():
        if len(team_rows) < 2:
            continue
        home_row = next((r for r in team_rows if "vs." in (r.get("matchup") or "")), None)
        away_row = next((r for r in team_rows if "@" in (r.get("matchup") or "")), None)
        if home_row is None or away_row is None:
            home_row, away_row = team_rows[0], team_rows[1]

        try:
            home_score = float(home_row["pts"])
            away_score = float(away_row["pts"])
        except Exception:
            continue

        games.append(
            {
                "season": home_row["season"],
                "game_id": game_id,
                "game_date": home_row["game_date"],
                "home_team": home_row["team_abbr"],
                "away_team": away_row["team_abbr"],
                "home_score": home_score,
                "away_score": away_score,
            }
        )
    games.sort(key=lambda g: (g["game_date"], g["game_id"]))
    return games


def _build_xy(
    games: List[dict],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build split model inputs and targets from historical games."""
    x_rows: Dict[str, List[List[float]]] = {group: [] for group in FEATURE_GROUPS}
    y_win: List[int] = []
    y_spread: List[float] = []
    y_total: List[float] = []

    for game in games:
        features = build_game_features(
            home_team=game["home_team"],
            away_team=game["away_team"],
            game_date=game["game_date"],
        )
        for group in FEATURE_GROUPS:
            x_rows[group].append(build_feature_row(features, group))
        margin = game["home_score"] - game["away_score"]
        y_win.append(1 if margin > 0 else 0)
        y_spread.append(margin)
        y_total.append(game["home_score"] + game["away_score"])

    return (
        np.array(x_rows["elo"], dtype=float),
        np.array(x_rows["stats"], dtype=float),
        np.array(x_rows["schedule"], dtype=float),
        np.array(y_win, dtype=int),
        np.array(y_spread, dtype=float),
        np.array(y_total, dtype=float),
    )


def train_from_history(seasons: Optional[List[str]] = None) -> dict:
    """Build historical dataset and train ensemble models."""
    _, default_seasons = load_seasons()
    seasons = seasons or default_seasons

    games = _load_training_games(seasons)
    if not games:
        try:
            refresh_team_stats(seasons)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Unable to refresh team stats before training: {exc}",
                "games": 0,
            }
        games = _load_training_games(seasons)

    if len(games) < 50:
        return {
            "ok": False,
            "error": "Not enough historical games to train models",
            "games": len(games),
        }

    X_elo, X_stats, X_sched, y_win, y_spread, y_total = _build_xy(games)
    if len(np.unique(y_win)) < 2:
        return {
            "ok": False,
            "error": "Training labels contain only one class",
            "games": len(games),
        }

    train_ensemble_models(X_elo, X_stats, X_sched, y_win, y_spread, y_total)
    return {
        "ok": True,
        "games_used": int(len(games)),
        "features": FEATURE_GROUPS,
    }
