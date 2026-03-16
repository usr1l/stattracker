"""Bootstrap ELO ratings from historical team results."""
from typing import Dict, List, Optional

from market.db import get_db
from prediction.elo import apply_season_carryover, save_elo, update_elo_post_game
from prediction.team_stats import refresh_team_stats
from season import load_seasons


def _load_completed_games(seasons: List[str]) -> List[dict]:
    """Load game rows for selected seasons, grouped as one row per game."""
    conn = get_db()
    try:
        placeholders = ",".join("?" for _ in seasons)
        rows = conn.execute(
            f"""
            SELECT season, game_id, game_date, team_abbr, matchup, wl, pts
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
            # Fallback when matchup markers are absent.
            home_row, away_row = team_rows[0], team_rows[1]

        try:
            games.append(
                {
                    "season": home_row["season"],
                    "game_id": game_id,
                    "game_date": home_row["game_date"],
                    "home_team": home_row["team_abbr"],
                    "away_team": away_row["team_abbr"],
                    "home_score": int(float(home_row["pts"])),
                    "away_score": int(float(away_row["pts"])),
                }
            )
        except Exception:
            continue

    games.sort(key=lambda g: (g["game_date"], g["game_id"]))
    return games


def build_elo_from_history(seasons: Optional[List[str]] = None) -> Dict[str, float]:
    """Build and persist ELO ratings from historical results."""
    _, default_seasons = load_seasons()
    seasons = seasons or default_seasons

    games = _load_completed_games(seasons)
    if not games:
        refresh_team_stats(seasons)
        games = _load_completed_games(seasons)

    ratings: Dict[str, float] = {}
    current_season = None

    for game in games:
        season = game["season"]
        if current_season is None:
            current_season = season
        elif season != current_season:
            ratings = apply_season_carryover(ratings)
            current_season = season

        update_elo_post_game(
            game["home_team"],
            game["away_team"],
            game["home_score"],
            game["away_score"],
            ratings,
        )

    save_elo(ratings)
    return ratings

