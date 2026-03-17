"""Daily injury ETL and date-based team injury modifiers."""
import logging
import os
import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import BoxScoreSummaryV2, LeagueDashPlayerStats, ScoreboardV2
from nba_api.stats.static import teams as nba_teams

from market.db import get_db
from season import load_seasons

logger = logging.getLogger("stattracker.prediction.injuries")
OUT_STATUSES = {"OUT", "DOUBTFUL"}
DEFAULT_INJURY_SOURCES = (
    "https://www.espn.com/nba/injuries",
    "https://www.cbssports.com/nba/injuries/",
)
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)
_TEAMS = nba_teams.get_teams()
TEAM_LOOKUP = {
    **{team["abbreviation"].upper(): team["abbreviation"].upper() for team in _TEAMS},
    **{team["full_name"].upper(): team["abbreviation"].upper() for team in _TEAMS},
    **{team["nickname"].upper(): team["abbreviation"].upper() for team in _TEAMS},
    **{team["city"].upper(): team["abbreviation"].upper() for team in _TEAMS},
}
PLAYER_VALUE_CACHE: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _normalize_date(target_date: Optional[str] = None) -> str:
    """Return a YYYY-MM-DD date string."""
    if not target_date:
        return date.today().isoformat()
    return pd.to_datetime(target_date).strftime("%Y-%m-%d")


def _format_scoreboard_date(target_date: str) -> str:
    """Convert YYYY-MM-DD into the ScoreboardV2 MM/DD/YYYY format."""
    return datetime.strptime(target_date, "%Y-%m-%d").strftime("%m/%d/%Y")


def _normalize_team_abbr(value: Any) -> Optional[str]:
    """Convert a team string into a canonical abbreviation."""
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip().upper()
    return TEAM_LOOKUP.get(cleaned, cleaned if cleaned in TEAM_LOOKUP.values() else None)


def _normalize_player_name(value: Any) -> str:
    """Normalize player names for dictionary lookup."""
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def _scoreboard_context(target_date: str) -> Tuple[List[str], List[str]]:
    """Return scheduled game ids and team abbreviations for a date."""
    formatted = _format_scoreboard_date(target_date)
    try:
        df = ScoreboardV2(game_date=formatted).get_data_frames()[0]
    except TypeError:
        df = ScoreboardV2(game_date=formatted, day_offset=0).get_data_frames()[0]

    if df.empty:
        return [], []

    game_ids = [str(game_id) for game_id in df["GAME_ID"].dropna().astype(str).tolist()]
    teams = set()
    for column in ("HOME_TEAM_ABBREVIATION", "VISITOR_TEAM_ABBREVIATION"):
        if column in df.columns:
            teams.update(str(team).upper() for team in df[column].dropna().astype(str).tolist())
    return game_ids, sorted(teams)


def fetch_advanced_player_stats(season: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Fetch a player-value map using PIE when available, else NET_RATING / PLUS_MINUS."""
    current_season, _ = load_seasons()
    season = season or current_season
    if season in PLAYER_VALUE_CACHE:
        return PLAYER_VALUE_CACHE[season]

    try:
        endpoint = LeagueDashPlayerStats(
            season=season,
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
        )
        df = endpoint.league_dash_player_stats.get_data_frame()
    except Exception as exc:
        logger.warning("Unable to fetch advanced player stats for %s: %s", season, exc)
        PLAYER_VALUE_CACHE[season] = {}
        return PLAYER_VALUE_CACHE[season]

    if df.empty:
        PLAYER_VALUE_CACHE[season] = {}
        return PLAYER_VALUE_CACHE[season]

    value_column = next(
        (column for column in ("PIE", "NET_RATING", "PLUS_MINUS") if column in df.columns),
        None,
    )
    if value_column is None:
        PLAYER_VALUE_CACHE[season] = {}
        return PLAYER_VALUE_CACHE[season]

    mapping: Dict[str, Dict[str, Any]] = {}
    for row in df.to_dict(orient="records"):
        player_name = str(row.get("PLAYER_NAME") or "").strip()
        if not player_name:
            continue
        mapping[_normalize_player_name(player_name)] = {
            "player_name": player_name,
            "team_abbr": str(row.get("TEAM_ABBREVIATION") or "").upper(),
            "vorp": float(pd.to_numeric(row.get(value_column), errors="coerce") or 0.0),
            "value_metric": value_column,
        }

    PLAYER_VALUE_CACHE[season] = mapping
    return mapping


def _parse_status(cells: List[str]) -> Optional[str]:
    """Extract an injury status from a row of cell text."""
    for cell in cells:
        normalized = str(cell).upper()
        if "DOUBTFUL" in normalized:
            return "Doubtful"
        if re.search(r"\bOUT\b", normalized):
            return "Out"
    return None


def _parse_injury_rows_from_html(html: str) -> List[Dict[str, str]]:
    """Parse a generic injury page into raw player/team/status rows."""
    soup = BeautifulSoup(html, "html.parser")
    rows: List[Dict[str, str]] = []
    for tr in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
        if len(cells) < 2:
            continue
        status = _parse_status(cells)
        if status is None or status.upper() not in OUT_STATUSES:
            continue

        team_abbr = next((_normalize_team_abbr(cell) for cell in cells if _normalize_team_abbr(cell)), None)
        if not team_abbr:
            continue

        player_name = next(
            (
                cell
                for cell in cells
                if cell
                and not _normalize_team_abbr(cell)
                and _parse_status([cell]) is None
                and "COMMENT" not in cell.upper()
                and "INJURY" not in cell.upper()
            ),
            None,
        )
        if not player_name:
            continue

        rows.append(
            {
                "player_name": player_name,
                "team_abbr": team_abbr,
                "status": status,
            }
        )
    return rows


def _scrape_public_injury_report(target_date: str) -> List[Dict[str, str]]:
    """Try public injury-report pages first."""
    del target_date  # Public pages are usually "today" boards rather than date-parametrized.
    urls = [url.strip() for url in os.environ.get("INJURY_REPORT_URLS", ",".join(DEFAULT_INJURY_SOURCES)).split(",") if url.strip()]
    headers = {"User-Agent": USER_AGENT}
    for url in urls:
        try:
            response = requests.get(url, timeout=20, headers=headers)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("Unable to fetch public injury report %s: %s", url, exc)
            continue

        rows = _parse_injury_rows_from_html(response.text)
        if rows:
            logger.info("Parsed %s injury rows from %s", len(rows), url)
            return rows
    return []


def _fetch_boxscore_injury_report(target_date: str) -> List[Dict[str, str]]:
    """Fallback to the NBA inactive-player list for games on the target date."""
    game_ids, _ = _scoreboard_context(target_date)
    rows: List[Dict[str, str]] = []
    for game_id in game_ids:
        try:
            summary = BoxScoreSummaryV2(game_id=game_id)
        except Exception as exc:
            logger.warning("Unable to fetch inactive players for game %s: %s", game_id, exc)
            continue

        inactive_df = summary.inactive_players.get_data_frame()
        if inactive_df.empty:
            continue

        for record in inactive_df.to_dict(orient="records"):
            team_abbr = _normalize_team_abbr(record.get("TEAM_ABBREVIATION"))
            if not team_abbr:
                continue
            player_name = " ".join(
                part
                for part in [record.get("FIRST_NAME"), record.get("LAST_NAME")]
                if part and str(part).strip()
            ).strip()
            if not player_name:
                continue
            rows.append(
                {
                    "player_name": player_name,
                    "team_abbr": team_abbr,
                    "status": "Out",
                }
            )
    return rows


def _upsert_daily_injuries(target_date: str, rows: Iterable[Dict[str, Any]]) -> int:
    """Replace one day's raw injury report in SQLite."""
    rows = list(rows)
    conn = get_db()
    try:
        conn.execute("DELETE FROM daily_injuries WHERE date = ?", (target_date,))
        written = 0
        for row in rows:
            cursor = conn.execute(
                """
                INSERT INTO daily_injuries (date, player_name, team_abbr, status, vorp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    target_date,
                    row["player_name"],
                    row["team_abbr"],
                    row["status"],
                    row["vorp"],
                ),
            )
            written += max(cursor.rowcount, 0)
        conn.commit()
        return written
    finally:
        conn.close()


def fetch_daily_injury_report(target_date: Optional[str] = None, season: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch the date's raw injury report and store the filtered rows."""
    normalized_date = _normalize_date(target_date)
    player_values = fetch_advanced_player_stats(season=season)
    raw_rows = _scrape_public_injury_report(normalized_date)
    if not raw_rows:
        raw_rows = _fetch_boxscore_injury_report(normalized_date)

    deduped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in raw_rows:
        status = str(row["status"]).strip().title()
        if status.upper() not in OUT_STATUSES:
            continue
        team_abbr = _normalize_team_abbr(row["team_abbr"])
        player_name = str(row["player_name"]).strip()
        if not team_abbr or not player_name:
            continue
        player_value = player_values.get(_normalize_player_name(player_name), {})
        deduped[(player_name.upper(), team_abbr)] = {
            "date": normalized_date,
            "player_name": player_name,
            "team_abbr": team_abbr,
            "status": status,
            "vorp": float(player_value.get("vorp", 0.0)),
        }

    rows = sorted(deduped.values(), key=lambda row: (row["team_abbr"], row["player_name"]))
    _upsert_daily_injuries(normalized_date, rows)
    logger.info("Daily injury report stored for %s with %s rows.", normalized_date, len(rows))
    return rows


def _upsert_team_injury_impact(target_date: str, rows: Iterable[Dict[str, Any]]) -> int:
    """Replace one day's team injury modifiers in SQLite."""
    rows = list(rows)
    conn = get_db()
    try:
        conn.execute("DELETE FROM team_injury_impact WHERE date = ?", (target_date,))
        written = 0
        for row in rows:
            cursor = conn.execute(
                """
                INSERT INTO team_injury_impact (date, team_abbr, total_vorp_missing, injury_modifier)
                VALUES (?, ?, ?, ?)
                """,
                (
                    target_date,
                    row["team_abbr"],
                    row["total_vorp_missing"],
                    row["injury_modifier"],
                ),
            )
            written += max(cursor.rowcount, 0)
        conn.commit()
        return written
    finally:
        conn.close()


def calculate_team_injury_impact(target_date: Optional[str] = None, season: Optional[str] = None) -> Dict[str, Any]:
    """Sum the missing player value by team and store a negative modifier."""
    normalized_date = _normalize_date(target_date)
    injury_rows = fetch_daily_injury_report(normalized_date, season=season)
    _, scheduled_teams = _scoreboard_context(normalized_date)

    totals: Dict[str, float] = {}
    for row in injury_rows:
        totals.setdefault(row["team_abbr"], 0.0)
        totals[row["team_abbr"]] += float(row.get("vorp", 0.0))
    for team_abbr in scheduled_teams:
        totals.setdefault(team_abbr, 0.0)

    impact_rows = [
        {
            "team_abbr": team_abbr,
            "total_vorp_missing": round(total_missing, 4),
            "injury_modifier": round(-total_missing, 4),
        }
        for team_abbr, total_missing in sorted(totals.items())
    ]
    written = _upsert_team_injury_impact(normalized_date, impact_rows)
    result = {
        "date": normalized_date,
        "teams": len(impact_rows),
        "rows_written": written,
    }
    logger.info("Team injury impact calculated: %s", result)
    return result


def refresh_daily_injury_reports(target_date: Optional[str] = None) -> Dict[str, Any]:
    """Backward-compatible wrapper that fetches raw report and team impact together."""
    normalized_date = _normalize_date(target_date)
    injuries = fetch_daily_injury_report(normalized_date)
    impact = calculate_team_injury_impact(normalized_date)
    return {
        "date": normalized_date,
        "daily_injuries": len(injuries),
        "team_injury_impact": impact.get("teams", 0),
    }


def _lookup_injury_modifier(team_abbr: str, target_date: str) -> float:
    """Fetch one team's injury modifier for a given date."""
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT injury_modifier
            FROM team_injury_impact
            WHERE date = ? AND team_abbr = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (target_date, team_abbr.upper()),
        ).fetchone()
    finally:
        conn.close()

    if row is not None:
        return float(row["injury_modifier"] or 0.0)

    try:
        calculate_team_injury_impact(target_date)
    except Exception as exc:
        logger.warning("Unable to self-heal injury modifier for %s on %s: %s", team_abbr, target_date, exc)
        return 0.0

    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT injury_modifier
            FROM team_injury_impact
            WHERE date = ? AND team_abbr = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (target_date, team_abbr.upper()),
        ).fetchone()
    finally:
        conn.close()
    return float(row["injury_modifier"] or 0.0) if row else 0.0


def get_injury_summary(home_team: str, away_team: str, game_date: str) -> Dict[str, Any]:
    """Return home and away injury modifiers from the date-based injury impact table."""
    normalized_date = _normalize_date(game_date)
    home_modifier = _lookup_injury_modifier(home_team, normalized_date)
    away_modifier = _lookup_injury_modifier(away_team, normalized_date)
    return {
        "home_injury_impact": round(home_modifier, 4),
        "away_injury_impact": round(away_modifier, 4),
        "home_inactive_count": 0,
        "away_inactive_count": 0,
        "home_inactive_players": [],
        "away_inactive_players": [],
    }
