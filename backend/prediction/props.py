"""Advanced player props projection engine."""
from datetime import date
from typing import Any, Dict, Optional

from nba_api.stats.static import teams

from market.db import get_db
from prediction.team_stats import get_team_rolling_stats

SUPPORTED_PROP_STATS = {"PTS", "REB", "AST"}
LEAGUE_AVG_PACE = 98.0
_TEAMS = teams.get_teams()

_TEAM_LOOKUP = {
    **{team["abbreviation"].upper(): team["abbreviation"].upper() for team in _TEAMS},
    **{team["full_name"].upper(): team["abbreviation"].upper() for team in _TEAMS},
    **{team["nickname"].upper(): team["abbreviation"].upper() for team in _TEAMS},
}


def _normalize_team_abbr(team_value: str) -> str:
    """Map full names or nicknames to a standard team abbreviation."""
    cleaned = str(team_value).strip().upper()
    return _TEAM_LOOKUP.get(cleaned, cleaned)


def _get_player_position(player_id: int) -> str:
    """Fetch a player's normalized primary position from SQLite."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT position FROM player_positions WHERE player_id = ?",
            (int(player_id),),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise ValueError(f"No position data found for player_id={player_id}")
    return str(row["position"])


def _get_player_baseline(player_id: int, stat: str) -> Dict[str, float]:
    """Fetch the stored per-minute baseline and minutes projection for one stat."""
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT per_minute_rate, projected_minutes
            FROM player_baselines
            WHERE player_id = ? AND stat = ?
            """,
            (int(player_id), stat),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise ValueError(f"No baseline data found for player_id={player_id}, stat={stat}")

    return {
        "per_minute_rate": float(row["per_minute_rate"]),
        "projected_minutes": float(row["projected_minutes"]),
    }


def _get_defense_modifier(opponent_team: str, position: str, stat: str) -> float:
    """Fetch the stored defense-vs-position modifier, defaulting to neutral."""
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT modifier
            FROM opponent_defense_matrix
            WHERE team_abbr = ? AND position = ? AND stat = ?
            """,
            (opponent_team, position, stat),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return 1.0
    return float(row["modifier"])


def _get_pace_modifier(opponent_team: str, game_date: str) -> float:
    """Convert opponent rolling pace into a multiplicative modifier."""
    rolling = get_team_rolling_stats(opponent_team, game_date, window=10)
    pace = float(rolling.get("pace", LEAGUE_AVG_PACE))
    if pace <= 0:
        return 1.0
    return pace / LEAGUE_AVG_PACE


def project_player_stat(
    player_id: int,
    stat: str,
    opponent_team: str,
    game_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Project a player prop line using baseline, defense, and pace modifiers."""
    normalized_stat = str(stat).strip().upper()
    if normalized_stat not in SUPPORTED_PROP_STATS:
        raise ValueError(f"Unsupported stat '{stat}'. Supported stats: PTS, REB, AST")

    opponent_abbr = _normalize_team_abbr(opponent_team)
    projection_date = game_date or date.today().isoformat()
    position = _get_player_position(int(player_id))
    baseline = _get_player_baseline(int(player_id), normalized_stat)

    base_projection = baseline["per_minute_rate"] * baseline["projected_minutes"]
    defense_mod = _get_defense_modifier(opponent_abbr, position, normalized_stat)
    pace_mod = _get_pace_modifier(opponent_abbr, projection_date)
    projected_line = base_projection * defense_mod * pace_mod

    return {
        "player_id": int(player_id),
        "stat": normalized_stat,
        "position": position,
        "opponent_team": opponent_abbr,
        "projected_line": projected_line,
        "modifiers_applied": {
            "base_projection": base_projection,
            "opponent_defense_mod": defense_mod,
            "pace_mod": pace_mod,
        },
    }
