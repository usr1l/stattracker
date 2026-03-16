"""Schedule features (rest days, B2B) backed by LeagueGameFinder."""
from datetime import datetime
from typing import List, Optional

import pandas as pd
from nba_api.stats.endpoints import LeagueGameFinder

from market.db import get_db
from season import load_seasons


def _upsert_schedule_rows(rows: List[dict]) -> int:
    """Insert schedule rows into team_game_logs (upsert via INSERT OR IGNORE)."""
    conn = get_db()
    inserted = 0
    try:
        for row in rows:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO team_game_logs (
                    season, game_id, game_date, team_abbr, matchup, wl, pts, opp_pts,
                    off_rating, def_rating, net_rating, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'LeagueGameFinder')
                """,
                (
                    row["season"],
                    row["game_id"],
                    row["game_date"],
                    row["team_abbr"],
                    row.get("matchup"),
                    row.get("wl"),
                    row.get("pts"),
                    row.get("opp_pts"),
                    row.get("off_rating"),
                    row.get("def_rating"),
                    row.get("net_rating"),
                ),
            )
            if cursor.rowcount > 0:
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted


def refresh_team_schedule(seasons: Optional[List[str]] = None) -> int:
    """Fetch team schedule/results by season and store in team_game_logs."""
    _, default_seasons = load_seasons()
    seasons = seasons or default_seasons
    total_inserted = 0

    for season in seasons:
        try:
            df = LeagueGameFinder(
                season_nullable=season,
                season_type_nullable="Regular Season",
                player_or_team_abbreviation="T",
            ).get_data_frames()[0]
        except TypeError:
            # Compatibility fallback for older nba_api signatures.
            df = LeagueGameFinder(season_nullable=season).get_data_frames()[0]

        if df.empty:
            continue

        rows: List[dict] = []
        for _, raw in df.iterrows():
            game_id = str(raw.get("GAME_ID", ""))
            game_date = raw.get("GAME_DATE")
            team_abbr = raw.get("TEAM_ABBREVIATION")
            matchup = raw.get("MATCHUP")
            wl = raw.get("WL")
            pts = raw.get("PTS")
            plus_minus = raw.get("PLUS_MINUS")
            opp_pts = None
            if pts is not None and plus_minus is not None:
                try:
                    opp_pts = float(pts) - float(plus_minus)
                except Exception:
                    opp_pts = None

            try:
                parsed_date = pd.to_datetime(game_date).strftime("%Y-%m-%d")
            except Exception:
                parsed_date = str(game_date)

            if not game_id or not team_abbr or not parsed_date:
                continue

            rows.append(
                {
                    "season": season,
                    "game_id": game_id,
                    "game_date": parsed_date,
                    "team_abbr": str(team_abbr),
                    "matchup": str(matchup) if matchup is not None else None,
                    "wl": str(wl) if wl is not None else None,
                    "pts": float(pts) if pts is not None else None,
                    "opp_pts": opp_pts,
                    "off_rating": float(pts) if pts is not None else None,
                    "def_rating": opp_pts,
                    "net_rating": float(plus_minus) if plus_minus is not None else None,
                }
            )
        total_inserted += _upsert_schedule_rows(rows)
    return total_inserted


def get_rest_days(team_abbr: str, game_date: str) -> int:
    """Days since team's previous game. Returns 7 when no history exists."""
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT game_date
            FROM team_game_logs
            WHERE team_abbr = ? AND game_date < ?
            ORDER BY game_date DESC
            LIMIT 1
            """,
            (team_abbr.upper(), game_date),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return 7

    current = datetime.strptime(game_date, "%Y-%m-%d")
    last = datetime.strptime(row["game_date"], "%Y-%m-%d")
    diff_days = (current - last).days
    return max(diff_days, 0)


def is_back_to_back(team_abbr: str, game_date: str) -> bool:
    """True if team played the day before the given game date."""
    return get_rest_days(team_abbr, game_date) <= 1

