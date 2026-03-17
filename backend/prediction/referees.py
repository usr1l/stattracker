"""Referee assignment ETL and rolling bias metrics."""
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
from nba_api.stats.endpoints import BoxScoreSummaryV2, BoxScoreTraditionalV2, ScoreboardV2

from market.db import get_db

logger = logging.getLogger("stattracker.prediction.referees")
REFEREE_LOOKBACK_DAYS = int(os.environ.get("REFEREE_LOOKBACK_DAYS", "45"))
REFEREE_LOOKBACK_LIMIT = int(os.environ.get("REFEREE_LOOKBACK_LIMIT", "200"))
LEAGUE_AVG_TOTAL_POINTS = float(os.environ.get("LEAGUE_AVG_TOTAL_POINTS", "228.0"))
LEAGUE_AVG_TOTAL_FOULS = float(os.environ.get("LEAGUE_AVG_TOTAL_FOULS", "39.0"))


def _normalize_date(target_date: Optional[str] = None) -> str:
    """Return a YYYY-MM-DD date string."""
    if not target_date:
        return date.today().isoformat()
    return pd.to_datetime(target_date).strftime("%Y-%m-%d")


def _format_scoreboard_date(target_date: str) -> str:
    """Convert YYYY-MM-DD into the ScoreboardV2 MM/DD/YYYY format."""
    return datetime.strptime(target_date, "%Y-%m-%d").strftime("%m/%d/%Y")


def _scoreboard_game_ids(target_date: str) -> List[str]:
    """Fetch scheduled game ids for a single date."""
    formatted = _format_scoreboard_date(target_date)
    try:
        df = ScoreboardV2(game_date=formatted).get_data_frames()[0]
    except TypeError:
        df = ScoreboardV2(game_date=formatted, day_offset=0).get_data_frames()[0]

    if df.empty or "GAME_ID" not in df.columns:
        return []
    return [str(game_id) for game_id in df["GAME_ID"].dropna().astype(str).tolist()]


def _recent_completed_game_ids(
    lookback_days: int = REFEREE_LOOKBACK_DAYS,
    limit: int = REFEREE_LOOKBACK_LIMIT,
) -> List[str]:
    """Load recent completed game ids from the local team log cache."""
    cutoff = (date.today() - timedelta(days=max(int(lookback_days), 1))).isoformat()
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT game_id
            FROM team_game_logs
            WHERE game_date >= ?
            ORDER BY game_date DESC
            LIMIT ?
            """,
            (cutoff, int(limit)),
        ).fetchall()
    finally:
        conn.close()
    return [str(row["game_id"]) for row in rows]


def _safe_summary(game_id: str):
    """Fetch BoxScoreSummaryV2 with a quiet failure mode."""
    try:
        return BoxScoreSummaryV2(game_id=game_id)
    except Exception as exc:
        logger.warning("Unable to fetch referee summary for game %s: %s", game_id, exc)
        return None


def _safe_traditional(game_id: str):
    """Fetch BoxScoreTraditionalV2 with a quiet failure mode."""
    try:
        return BoxScoreTraditionalV2(game_id=game_id)
    except Exception as exc:
        logger.warning("Unable to fetch traditional box score for game %s: %s", game_id, exc)
        return None


def _parse_game_context(game_id: str) -> Dict[str, Any]:
    """Fetch the official assignments and game metrics for one game."""
    summary = _safe_summary(game_id)
    if summary is None:
        return {"officials": [], "game_date": None, "home_team": None, "away_team": None}

    officials_df = summary.officials.get_data_frame()
    game_summary_df = summary.game_summary.get_data_frame()
    line_score_df = summary.line_score.get_data_frame()
    if game_summary_df.empty or line_score_df.empty:
        return {"officials": [], "game_date": None, "home_team": None, "away_team": None}

    game_summary = game_summary_df.iloc[0]
    try:
        game_date = pd.to_datetime(game_summary.get("GAME_DATE_EST")).strftime("%Y-%m-%d")
    except Exception:
        game_date = None

    home_team_id = int(game_summary.get("HOME_TEAM_ID"))
    away_team_id = int(game_summary.get("VISITOR_TEAM_ID"))
    home_row = line_score_df[line_score_df["TEAM_ID"] == home_team_id]
    away_row = line_score_df[line_score_df["TEAM_ID"] == away_team_id]
    if home_row.empty or away_row.empty:
        return {"officials": [], "game_date": game_date, "home_team": None, "away_team": None}

    home_line = home_row.iloc[0]
    away_line = away_row.iloc[0]
    home_team = str(home_line.get("TEAM_ABBREVIATION") or "").upper()
    away_team = str(away_line.get("TEAM_ABBREVIATION") or "").upper()

    home_points = pd.to_numeric(home_line.get("PTS"), errors="coerce")
    away_points = pd.to_numeric(away_line.get("PTS"), errors="coerce")
    total_points = None
    home_win = None
    if pd.notna(home_points) and pd.notna(away_points):
        total_points = float(home_points + away_points)
        home_win = 1 if float(home_points) > float(away_points) else 0

    total_fouls = None
    traditional = _safe_traditional(game_id)
    if traditional is not None:
        team_stats_df = traditional.team_stats.get_data_frame()
        if not team_stats_df.empty and "PF" in team_stats_df.columns:
            home_stats = team_stats_df[team_stats_df["TEAM_ID"] == home_team_id]
            away_stats = team_stats_df[team_stats_df["TEAM_ID"] == away_team_id]
            if not home_stats.empty and not away_stats.empty:
                home_pf = pd.to_numeric(home_stats.iloc[0].get("PF"), errors="coerce")
                away_pf = pd.to_numeric(away_stats.iloc[0].get("PF"), errors="coerce")
                if pd.notna(home_pf) and pd.notna(away_pf):
                    total_fouls = float(home_pf + away_pf)

    officials: List[Dict[str, Any]] = []
    for record in officials_df.to_dict(orient="records"):
        official_id = record.get("OFFICIAL_ID")
        if official_id is None:
            continue
        full_name = " ".join(
            part
            for part in [record.get("FIRST_NAME"), record.get("LAST_NAME")]
            if part and str(part).strip()
        ).strip()
        officials.append(
            {
                "game_id": str(game_id),
                "official_id": int(official_id),
                "official_name": full_name or f"Official {official_id}",
                "game_date": game_date,
                "home_team": home_team,
                "away_team": away_team,
                "home_win": home_win,
                "total_points": total_points,
                "total_fouls": total_fouls,
            }
        )

    return {
        "officials": officials,
        "game_date": game_date,
        "home_team": home_team,
        "away_team": away_team,
    }


def _upsert_referee_game_logs(rows: Iterable[Dict[str, Any]]) -> int:
    """Insert or replace referee assignment rows."""
    rows = list(rows)
    if not rows:
        return 0

    conn = get_db()
    written = 0
    try:
        for row in rows:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO referee_game_logs (
                    game_id, official_id, official_name, game_date, home_team, away_team,
                    home_win, total_points, total_fouls, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    row["game_id"],
                    row["official_id"],
                    row["official_name"],
                    row.get("game_date"),
                    row.get("home_team"),
                    row.get("away_team"),
                    row.get("home_win"),
                    row.get("total_points"),
                    row.get("total_fouls"),
                ),
            )
            written += max(cursor.rowcount, 0)
        conn.commit()
    finally:
        conn.close()
    return written


def refresh_referee_games(game_ids: Iterable[str]) -> Dict[str, int]:
    """Fetch and cache referee assignments for a set of game ids."""
    processed = 0
    written = 0
    for game_id in {str(game_id) for game_id in game_ids if game_id}:
        context = _parse_game_context(game_id)
        processed += 1
        written += _upsert_referee_game_logs(context["officials"])
    return {"games_processed": processed, "rows_written": written}


def rebuild_referee_stats(lookback_days: int = REFEREE_LOOKBACK_DAYS) -> Dict[str, int]:
    """Aggregate rolling bias metrics by official."""
    cutoff = (date.today() - timedelta(days=max(int(lookback_days), 1))).isoformat()
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT
                official_id,
                official_name,
                COUNT(1) AS games_officiated,
                AVG(CAST(home_win AS REAL)) AS home_win_pct,
                AVG(total_points) AS avg_total_points,
                AVG(total_fouls) AS avg_total_fouls,
                MAX(game_date) AS last_game_date
            FROM referee_game_logs
            WHERE game_date >= ? AND home_win IS NOT NULL
            GROUP BY official_id, official_name
            """,
            (cutoff,),
        ).fetchall()

        conn.execute("DELETE FROM referee_stats")
        for row in rows:
            avg_total_points = float(row["avg_total_points"] or 0.0)
            avg_total_fouls = float(row["avg_total_fouls"] or 0.0)
            home_win_pct = float(row["home_win_pct"] or 0.5)
            over_index = (
                (avg_total_points - LEAGUE_AVG_TOTAL_POINTS) / LEAGUE_AVG_TOTAL_POINTS
                if LEAGUE_AVG_TOTAL_POINTS > 0
                else 0.0
            )
            home_bias = home_win_pct - 0.5
            conn.execute(
                """
                INSERT INTO referee_stats (
                    official_id, official_name, games_officiated, home_win_pct,
                    avg_total_points, avg_fouls_called, over_index, home_bias,
                    last_game_date, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    int(row["official_id"]),
                    row["official_name"],
                    int(row["games_officiated"]),
                    home_win_pct,
                    avg_total_points,
                    avg_total_fouls,
                    over_index,
                    home_bias,
                    row["last_game_date"],
                ),
            )
        conn.commit()
        return {"officials": len(rows)}
    finally:
        conn.close()


def refresh_daily_referee_assignments(target_date: Optional[str] = None) -> Dict[str, Any]:
    """Fetch today's assignments, backfill recent history, and rebuild referee stats."""
    normalized_date = _normalize_date(target_date)
    today_games = _scoreboard_game_ids(normalized_date)
    recent_games = _recent_completed_game_ids()
    refreshed = refresh_referee_games(list(today_games) + list(recent_games))
    aggregates = rebuild_referee_stats()
    result = {
        "date": normalized_date,
        "today_games": len(today_games),
        "historical_games": len(recent_games),
        **refreshed,
        **aggregates,
    }
    logger.info("Referee refresh complete: %s", result)
    return result


def get_referee_bias(game_id: Optional[str]) -> Dict[str, Any]:
    """Return aggregate referee home/total bias for a game assignment."""
    if not game_id:
        return {
            "ref_home_bias": 0.0,
            "ref_total_bias": 0.0,
            "ref_foul_bias": 0.0,
            "assigned_referees": [],
        }

    conn = get_db()
    try:
        assignment_rows = conn.execute(
            """
            SELECT official_id, official_name
            FROM referee_game_logs
            WHERE game_id = ?
            ORDER BY official_name ASC
            """,
            (str(game_id),),
        ).fetchall()
    finally:
        conn.close()

    if not assignment_rows:
        refresh_referee_games([game_id])
        conn = get_db()
        try:
            assignment_rows = conn.execute(
                """
                SELECT official_id, official_name
                FROM referee_game_logs
                WHERE game_id = ?
                ORDER BY official_name ASC
                """,
                (str(game_id),),
            ).fetchall()
        finally:
            conn.close()

    if not assignment_rows:
        return {
            "ref_home_bias": 0.0,
            "ref_total_bias": 0.0,
            "ref_foul_bias": 0.0,
            "assigned_referees": [],
        }

    official_ids = [int(row["official_id"]) for row in assignment_rows]
    placeholders = ",".join("?" for _ in official_ids)
    conn = get_db()
    try:
        stats_rows = conn.execute(
            f"""
            SELECT home_bias, over_index, avg_fouls_called
            FROM referee_stats
            WHERE official_id IN ({placeholders})
            """,
            tuple(official_ids),
        ).fetchall()
    finally:
        conn.close()

    if not stats_rows:
        rebuild_referee_stats()
        conn = get_db()
        try:
            stats_rows = conn.execute(
                f"""
                SELECT home_bias, over_index, avg_fouls_called
                FROM referee_stats
                WHERE official_id IN ({placeholders})
                """,
                tuple(official_ids),
            ).fetchall()
        finally:
            conn.close()

    if not stats_rows:
        stats_rows = []

    foul_bias = 0.0
    if stats_rows and LEAGUE_AVG_TOTAL_FOULS > 0:
        foul_bias = (
            sum(float(row["avg_fouls_called"] or 0.0) for row in stats_rows) / len(stats_rows)
            - LEAGUE_AVG_TOTAL_FOULS
        ) / LEAGUE_AVG_TOTAL_FOULS

    return {
        "ref_home_bias": round(
            sum(float(row["home_bias"] or 0.0) for row in stats_rows) / len(stats_rows), 4
        )
        if stats_rows
        else 0.0,
        "ref_total_bias": round(
            sum(float(row["over_index"] or 0.0) for row in stats_rows) / len(stats_rows), 4
        )
        if stats_rows
        else 0.0,
        "ref_foul_bias": round(foul_bias, 4),
        "assigned_referees": [str(row["official_name"]) for row in assignment_rows],
    }
