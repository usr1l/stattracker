"""Team-level data ETL and rolling metric helpers."""
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
from nba_api.stats.endpoints import TeamGameLogs

from market.db import get_db
from season import load_seasons


def _to_float(value: Any) -> Optional[float]:
    """Convert values to float safely."""
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _standardize_team_logs(df: pd.DataFrame, season: str) -> List[dict]:
    """Map TeamGameLogs rows into the team_game_logs schema."""
    if df.empty:
        return []

    rows: List[dict] = []
    for _, row in df.iterrows():
        team_abbr = row.get("TEAM_ABBREVIATION") or row.get("TEAM_ABBREV")
        game_id = str(row.get("GAME_ID", ""))
        game_date = row.get("GAME_DATE")
        matchup = row.get("MATCHUP")
        wl = row.get("WL")

        pts = _to_float(row.get("PTS"))
        plus_minus = _to_float(row.get("PLUS_MINUS"))
        opp_pts = _to_float(row.get("OPP_PTS"))
        if opp_pts is None and pts is not None and plus_minus is not None:
            # PLUS_MINUS = team points - opponent points
            opp_pts = pts - plus_minus

        fgm = _to_float(row.get("FGM"))
        fg3m = _to_float(row.get("FG3M"))
        fga = _to_float(row.get("FGA"))
        tov = _to_float(row.get("TOV"))
        fta = _to_float(row.get("FTA"))

        efg_pct = _to_float(row.get("EFG_PCT"))
        if efg_pct is None and fga and fga > 0 and fgm is not None and fg3m is not None:
            efg_pct = (fgm + 0.5 * fg3m) / fga

        pace = _to_float(row.get("PACE"))
        if pace is None and fga is not None and tov is not None and fta is not None:
            # Possessions proxy when pace not present.
            pace = fga + tov + (0.44 * fta)

        off_rating = _to_float(row.get("OFF_RATING"))
        def_rating = _to_float(row.get("DEF_RATING"))
        net_rating = _to_float(row.get("NET_RATING"))
        if net_rating is None and off_rating is not None and def_rating is not None:
            net_rating = off_rating - def_rating
        if net_rating is None and plus_minus is not None:
            net_rating = plus_minus

        tov_pct = _to_float(row.get("TOV_PCT"))
        if tov_pct is None and pace and pace > 0 and tov is not None:
            tov_pct = tov / pace

        if game_date is not None:
            try:
                parsed = pd.to_datetime(game_date)
                game_date = parsed.strftime("%Y-%m-%d")
            except Exception:
                game_date = str(game_date)

        if not team_abbr or not game_id or not game_date:
            continue

        rows.append(
            {
                "season": season,
                "game_id": game_id,
                "game_date": str(game_date),
                "team_abbr": str(team_abbr),
                "matchup": str(matchup) if matchup is not None else None,
                "wl": str(wl) if wl is not None else None,
                "pts": pts,
                "opp_pts": opp_pts,
                "pace": pace,
                "efg_pct": efg_pct,
                "tov_pct": tov_pct,
                "off_rating": off_rating,
                "def_rating": def_rating,
                "net_rating": net_rating,
            }
        )
    return rows


def fetch_team_logs_for_season(season: str) -> List[dict]:
    """Fetch all team game logs for a season from nba_api."""
    try:
        df = TeamGameLogs(
            season_nullable=season,
            season_type_nullable="Regular Season",
        ).get_data_frames()[0]
    except TypeError:
        # Compatibility fallback for nba_api signature differences.
        df = TeamGameLogs(season=season).get_data_frames()[0]
    return _standardize_team_logs(df, season)


def store_team_logs(rows: Iterable[dict]) -> int:
    """Insert standardized team logs into SQLite."""
    inserted = 0
    conn = get_db()
    try:
        for row in rows:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO team_game_logs (
                    season, game_id, game_date, team_abbr, matchup, wl, pts, opp_pts,
                    pace, efg_pct, tov_pct, off_rating, def_rating, net_rating, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'TeamGameLogs')
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
                    row.get("pace"),
                    row.get("efg_pct"),
                    row.get("tov_pct"),
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


def refresh_team_stats(seasons: Optional[List[str]] = None) -> int:
    """Fetch and persist team logs for given seasons."""
    _, default_seasons = load_seasons()
    seasons = seasons or default_seasons
    total_inserted = 0
    for season in seasons:
        rows = fetch_team_logs_for_season(season)
        total_inserted += store_team_logs(rows)
    return total_inserted


def has_team_game_logs() -> bool:
    """Return True when team_game_logs has at least one row."""
    conn = get_db()
    try:
        row = conn.execute("SELECT COUNT(1) AS n FROM team_game_logs").fetchone()
        return bool(row and row["n"] > 0)
    finally:
        conn.close()


def get_team_rolling_stats(team_abbr: str, game_date: str, window: int = 10) -> Dict[str, float]:
    """Calculate rolling averages for a team before a given game date."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT off_rating, def_rating, net_rating, pace, efg_pct, tov_pct, pts, opp_pts
            FROM team_game_logs
            WHERE team_abbr = ? AND game_date < ?
            ORDER BY game_date DESC
            LIMIT ?
            """,
            (team_abbr.upper(), game_date, int(window)),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {
            "off_rating": 110.0,
            "def_rating": 110.0,
            "net_rating": 0.0,
            "pace": 98.0,
            "efg_pct": 0.54,
            "tov_pct": 0.14,
        }

    df = pd.DataFrame([dict(r) for r in rows])

    if "off_rating" not in df or df["off_rating"].isna().all():
        df["off_rating"] = df["pts"]
    if "def_rating" not in df or df["def_rating"].isna().all():
        df["def_rating"] = df["opp_pts"]
    if "net_rating" not in df or df["net_rating"].isna().all():
        df["net_rating"] = df["off_rating"] - df["def_rating"]
    if "pace" not in df or df["pace"].isna().all():
        df["pace"] = 98.0
    if "efg_pct" not in df or df["efg_pct"].isna().all():
        df["efg_pct"] = 0.54
    if "tov_pct" not in df or df["tov_pct"].isna().all():
        df["tov_pct"] = 0.14

    return {
        "off_rating": float(df["off_rating"].mean()),
        "def_rating": float(df["def_rating"].mean()),
        "net_rating": float(df["net_rating"].mean()),
        "pace": float(df["pace"].mean()),
        "efg_pct": float(df["efg_pct"].mean()),
        "tov_pct": float(df["tov_pct"].mean()),
    }

