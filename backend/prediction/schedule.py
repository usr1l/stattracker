"""Schedule features (rest days, travel, B2B) backed by LeagueGameFinder."""
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from typing import Dict, List, Optional, Tuple

import pandas as pd
from nba_api.stats.endpoints import LeagueGameFinder

from market.db import get_db
from season import load_seasons

ARENA_COORDS: Dict[str, Tuple[float, float]] = {
    "ATL": (33.7573, -84.3963),
    "BOS": (42.3662, -71.0621),
    "BKN": (40.6826, -73.9754),
    "CHA": (35.2251, -80.8392),
    "CHI": (41.8807, -87.6742),
    "CLE": (41.4965, -81.6882),
    "DAL": (32.7905, -96.8103),
    "DEN": (39.7487, -105.0077),
    "DET": (42.3410, -83.0551),
    "GSW": (37.7680, -122.3877),
    "HOU": (29.7508, -95.3621),
    "IND": (39.7639, -86.1555),
    "LAC": (33.9535, -118.3392),
    "LAL": (34.0430, -118.2673),
    "MEM": (35.1382, -90.0505),
    "MIA": (25.7814, -80.1870),
    "MIL": (43.0451, -87.9172),
    "MIN": (44.9795, -93.2760),
    "NOP": (29.9490, -90.0821),
    "NYK": (40.7505, -73.9934),
    "OKC": (35.4634, -97.5151),
    "ORL": (28.5392, -81.3839),
    "PHI": (39.9012, -75.1719),
    "PHX": (33.4457, -112.0712),
    "POR": (45.5316, -122.6668),
    "SAC": (38.5802, -121.4996),
    "SAS": (29.4269, -98.4375),
    "TOR": (43.6435, -79.3791),
    "UTA": (40.7683, -111.9011),
    "WAS": (38.8981, -77.0209),
}

EARTH_RADIUS_MILES = 3958.8


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


def haversine_miles(origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
    """Calculate great-circle distance between two lat/lon points in miles."""
    origin_lat, origin_lon = origin
    dest_lat, dest_lon = destination
    lat_delta = radians(dest_lat - origin_lat)
    lon_delta = radians(dest_lon - origin_lon)
    a = (
        sin(lat_delta / 2) ** 2
        + cos(radians(origin_lat)) * cos(radians(dest_lat)) * sin(lon_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * asin(sqrt(a))


def _extract_opponent_from_matchup(matchup: Optional[str]) -> Optional[str]:
    """Pull the opponent abbreviation from a matchup string."""
    if not matchup:
        return None
    parts = str(matchup).strip().upper().split()
    if not parts:
        return None
    opponent = parts[-1]
    return opponent if opponent in ARENA_COORDS else None


def _get_previous_game_row(team_abbr: str, game_date: str):
    """Return the team's last stored game row before a target date."""
    conn = get_db()
    try:
        return conn.execute(
            """
            SELECT game_date, matchup
            FROM team_game_logs
            WHERE team_abbr = ? AND game_date < ?
            ORDER BY game_date DESC
            LIMIT 1
            """,
            (team_abbr.upper(), game_date),
        ).fetchone()
    finally:
        conn.close()


def _get_previous_venue_team(team_abbr: str, game_date: str) -> Optional[str]:
    """Resolve the venue team abbreviation for the team's previous game."""
    row = _get_previous_game_row(team_abbr, game_date)
    if not row:
        return None

    matchup = str(row["matchup"] or "").upper()
    if "VS." in matchup:
        return team_abbr.upper()
    if "@" in matchup:
        return _extract_opponent_from_matchup(matchup)
    return None


def get_rest_days(team_abbr: str, game_date: str) -> int:
    """Days since team's previous game. Returns 7 when no history exists."""
    row = _get_previous_game_row(team_abbr, game_date)

    if not row:
        return 7

    current = datetime.strptime(game_date, "%Y-%m-%d")
    last = datetime.strptime(row["game_date"], "%Y-%m-%d")
    diff_days = (current - last).days
    return max(diff_days, 0)


def is_back_to_back(team_abbr: str, game_date: str) -> bool:
    """True if team played the day before the given game date."""
    return get_rest_days(team_abbr, game_date) <= 1


def get_distance_traveled(team_abbr: str, current_venue_team: str, game_date: str) -> float:
    """Distance from a team's previous game venue to the current venue in miles."""
    previous_venue_team = _get_previous_venue_team(team_abbr, game_date)
    if not previous_venue_team:
        return 0.0

    origin = ARENA_COORDS.get(previous_venue_team.upper())
    destination = ARENA_COORDS.get(current_venue_team.upper())
    if origin is None or destination is None:
        return 0.0
    return round(haversine_miles(origin, destination), 2)


def get_schedule_context(home_team: str, away_team: str, game_date: str) -> Dict[str, float]:
    """Return the full rest, back-to-back, and travel feature block for a matchup."""
    home_abbr = home_team.upper()
    away_abbr = away_team.upper()
    home_rest = get_rest_days(home_abbr, game_date)
    away_rest = get_rest_days(away_abbr, game_date)

    return {
        "home_rest_days": float(home_rest),
        "away_rest_days": float(away_rest),
        "home_b2b": 1.0 if home_rest <= 1 else 0.0,
        "away_b2b": 1.0 if away_rest <= 1 else 0.0,
        "home_distance_traveled": float(get_distance_traveled(home_abbr, home_abbr, game_date)),
        "away_distance_traveled": float(get_distance_traveled(away_abbr, home_abbr, game_date)),
    }
