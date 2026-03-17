"""Live in-game probability adjustment engine."""
from datetime import datetime, timedelta, timezone
from math import sqrt
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from nba_api.stats.static import teams

from market.db import get_db
from prediction.features import build_game_features
from prediction.model import predict

FULL_GAME_SECONDS = 48 * 60
EASTERN = ZoneInfo("America/New_York")
SCORE_SCALING_CONSTANT = 1.35
_TEAMS = teams.get_teams()
_TEAM_LOOKUP = {
    **{team["abbreviation"].upper(): team["abbreviation"].upper() for team in _TEAMS},
    **{team["full_name"].upper(): team["abbreviation"].upper() for team in _TEAMS},
    **{team["nickname"].upper(): team["abbreviation"].upper() for team in _TEAMS},
    "LOS ANGELES CLIPPERS": "LAC",
    "LA CLIPPERS": "LAC",
    "LOS ANGELES LAKERS": "LAL",
    "LA LAKERS": "LAL",
}


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse DB/API timestamps into UTC."""
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a numeric value into an inclusive range."""
    return max(lower, min(upper, float(value)))


def _round_or_none(value: Optional[float], digits: int = 4) -> Optional[float]:
    """Round optional floats safely."""
    if value is None:
        return None
    return round(float(value), digits)


def normalize_team_abbr(team_value: str) -> str:
    """Map team full names/nicknames into standard NBA abbreviations."""
    cleaned = str(team_value).strip().upper()
    return _TEAM_LOOKUP.get(cleaned, cleaned)


def decimal_odds_to_implied_prob(price: Optional[float]) -> Optional[float]:
    """Convert decimal odds into implied win probability."""
    if price is None:
        return None
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    if price <= 1.0:
        return None
    return 1.0 / price


def _game_date_from_state(state: Dict[str, Any]) -> str:
    """Infer the game date to use for pre-game model features."""
    commence_time = _parse_datetime(state.get("commence_time"))
    if commence_time is not None:
        return commence_time.astimezone(EASTERN).date().isoformat()

    last_updated = _parse_datetime(state.get("last_updated"))
    if last_updated is not None:
        return last_updated.astimezone(EASTERN).date().isoformat()

    return datetime.now(EASTERN).date().isoformat()


def _calculate_score_only_probability(point_diff: int, seconds_remaining: int) -> float:
    """Estimate win probability from score margin alone."""
    if seconds_remaining <= 0:
        if point_diff > 0:
            return 1.0
        if point_diff < 0:
            return 0.0
        return 0.5

    denominator = max(1.0, sqrt(max(float(seconds_remaining), 1.0)) * SCORE_SCALING_CONSTANT)
    score_prob = 0.5 + (float(point_diff) / denominator)
    return _clamp(score_prob, 0.01, 0.99)


def _blend_live_probability(pre_game_prob: float, point_diff: int, seconds_remaining: int) -> Dict[str, float]:
    """Blend pre-game strength with score-state reality using time decay."""
    time_weight = _clamp(seconds_remaining / FULL_GAME_SECONDS, 0.0, 1.0)
    score_prob = _calculate_score_only_probability(point_diff, seconds_remaining)
    live_prob = _clamp(
        (float(pre_game_prob) * time_weight) + (score_prob * (1.0 - time_weight)),
        0.0,
        1.0,
    )
    return {
        "time_weight": time_weight,
        "score_state_prob": score_prob,
        "live_prob": live_prob,
    }


def _get_live_state(game_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single live game state row."""
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT game_id, home_team, away_team, commence_time, home_score, away_score,
                   quarter, time_remaining_str, seconds_remaining, live_home_price,
                   live_home_point, last_updated
            FROM live_game_state
            WHERE game_id = ?
            """,
            (str(game_id),),
        ).fetchone()
    finally:
        conn.close()

    return dict(row) if row else None


def _get_recent_live_states(max_age_hours: int = 8) -> List[Dict[str, Any]]:
    """Fetch fresh active live states for the API."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT game_id, home_team, away_team, commence_time, home_score, away_score,
                   quarter, time_remaining_str, seconds_remaining, live_home_price,
                   live_home_point, last_updated
            FROM live_game_state
            WHERE COALESCE(seconds_remaining, 0) > 0
            ORDER BY seconds_remaining ASC, last_updated DESC
            """
        ).fetchall()
    finally:
        conn.close()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        last_updated = _parse_datetime(payload.get("last_updated"))
        if last_updated is not None and last_updated < cutoff:
            continue
        filtered.append(payload)
    return filtered


def _calculate_projection_from_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Build one live projection payload from the stored state."""
    home_abbr = normalize_team_abbr(str(state["home_team"]))
    away_abbr = normalize_team_abbr(str(state["away_team"]))
    game_date = _game_date_from_state(state)

    features = build_game_features(home_abbr, away_abbr, game_date, game_id=str(state["game_id"]))
    pre_game_prob = float(predict(features)["home_win_prob"])

    home_score = int(state.get("home_score") or 0)
    away_score = int(state.get("away_score") or 0)
    seconds_remaining = max(0, int(state.get("seconds_remaining") or 0))
    point_diff = home_score - away_score
    blend = _blend_live_probability(pre_game_prob, point_diff, seconds_remaining)

    live_home_price = (
        float(state["live_home_price"]) if state.get("live_home_price") is not None else None
    )
    live_implied_prob = decimal_odds_to_implied_prob(live_home_price)
    edge = None if live_implied_prob is None else blend["live_prob"] - live_implied_prob

    quarter = str(state.get("quarter") or "").strip()
    time_remaining = str(state.get("time_remaining_str") or "").strip()
    if quarter and time_remaining:
        clock = f"{quarter} {time_remaining}"
    else:
        clock = quarter or time_remaining or "Live"

    return {
        "game_id": str(state["game_id"]),
        "matchup": f"{home_abbr} vs {away_abbr}",
        "score": {
            "home": home_score,
            "away": away_score,
        },
        "clock": clock,
        "model": {
            "pre_game_prob": _round_or_none(pre_game_prob),
            "score_state_prob": _round_or_none(blend["score_state_prob"]),
            "time_weight": _round_or_none(blend["time_weight"]),
            "live_prob": _round_or_none(blend["live_prob"]),
        },
        "market": {
            "live_home_price": _round_or_none(live_home_price, 3),
            "live_implied_prob": _round_or_none(live_implied_prob),
            "live_spread": _round_or_none(
                float(state["live_home_point"]) if state.get("live_home_point") is not None else None,
                2,
            ),
        },
        "edge": _round_or_none(edge),
    }


def calculate_live_win_prob(game_id: str) -> Dict[str, Any]:
    """Calculate the live blended win probability for one game."""
    state = _get_live_state(game_id)
    if state is None:
        raise ValueError(f"No live game state found for game_id={game_id}")
    return _calculate_projection_from_state(state)


def list_live_games(max_age_hours: int = 8) -> List[Dict[str, Any]]:
    """Return all current live-game projections with sportsbook edge."""
    projections: List[Dict[str, Any]] = []
    for state in _get_recent_live_states(max_age_hours=max_age_hours):
        try:
            projections.append(_calculate_projection_from_state(state))
        except Exception:
            continue

    projections.sort(
        key=lambda game: abs(float(game["edge"])) if game.get("edge") is not None else -1.0,
        reverse=True,
    )
    return projections
