"""Live in-game polling client for The Odds API."""
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

import requests

from app.logger import get_logger
from app.services.scoreboard import get_scoreboard_game_header
from market.db import get_db

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com/v4"
SPORT = "basketball_nba"
TARGET_BOOKMAKER = "draftkings"
REGIONS = "us"
LIVE_MARKETS = "h2h,spreads"
FULL_GAME_SECONDS = 48 * 60
ESTIMATED_BROADCAST_SECONDS = int(2.5 * 60 * 60)
EASTERN = ZoneInfo("America/New_York")
LIVE_WINDOW_START_MINUTES = int(os.environ.get("LIVE_WINDOW_START_MINUTES", str((18 * 60) + 30)))
LIVE_WINDOW_END_MINUTES = int(os.environ.get("LIVE_WINDOW_END_MINUTES", str((1 * 60) + 30)))
logger = get_logger(__name__)


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    """Parse an ISO-ish timestamp into UTC."""
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _coerce_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """Convert a raw value into an integer safely."""
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Convert a raw value into a float safely."""
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _request_json(path: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Issue a GET request to The Odds API and return a JSON list."""
    if not ODDS_API_KEY:
        logger.warning("ODDS_API_KEY not set. Skipping live polling.")
        return []

    url = f"{BASE_URL}{path}"
    request_params = dict(params)
    request_params["apiKey"] = ODDS_API_KEY

    try:
        resp = requests.get(url, params=request_params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        logger.error("Error fetching live data from The Odds API: %s", exc)
        return []

    return payload if isinstance(payload, list) else []


def _format_scoreboard_date(target_date) -> str:
    """Convert a date object into the ScoreboardV2 expected format."""
    return target_date.strftime("%m/%d/%Y")


def _has_recent_live_state(now_utc: datetime, max_age_hours: int = 4) -> bool:
    """Return True when the DB already has a fresh active live snapshot."""
    cutoff = (now_utc - timedelta(hours=max_age_hours)).isoformat()
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT 1
            FROM live_game_state
            WHERE COALESCE(seconds_remaining, 0) > 0
              AND datetime(COALESCE(last_updated, '1970-01-01T00:00:00+00:00')) >= datetime(?)
            LIMIT 1
            """,
            (cutoff,),
        ).fetchone()
    finally:
        conn.close()
    return row is not None


def _is_within_live_window(now_est: datetime) -> bool:
    """Return True when current Eastern time is inside the local polling window."""
    current_minutes = (now_est.hour * 60) + now_est.minute
    return current_minutes >= LIVE_WINDOW_START_MINUTES or current_minutes <= LIVE_WINDOW_END_MINUTES


def _candidate_scoreboard_dates(now_est: datetime) -> List[date]:
    """Choose scoreboard dates to inspect for the overnight live window."""
    dates = [now_est.date()]
    if (now_est.hour * 60) + now_est.minute <= LIVE_WINDOW_END_MINUTES:
        dates.insert(0, now_est.date() - timedelta(days=1))
    return dates


def _scoreboard_has_games(target_date) -> Optional[bool]:
    """Return whether the NBA scoreboard has any games for a given date."""
    formatted_date = _format_scoreboard_date(target_date)
    try:
        df = get_scoreboard_game_header(formatted_date)
    except Exception as exc:
        logger.warning("Unable to read scoreboard for %s: %s", formatted_date, exc)
        return None
    return not df.empty


def are_games_currently_active(now_utc: Optional[datetime] = None) -> bool:
    """Return True when local conditions justify hitting the live Odds API."""
    if os.environ.get("FORCE_LIVE_POLL", "0") == "1":
        return True

    now_utc = now_utc or datetime.now(timezone.utc)
    now_est = now_utc.astimezone(EASTERN)

    if _has_recent_live_state(now_utc):
        return True

    if not _is_within_live_window(now_est):
        return False

    scoreboard_results = [_scoreboard_has_games(target_date) for target_date in _candidate_scoreboard_dates(now_est)]
    if any(result is True for result in scoreboard_results):
        return True

    # If scoreboard lookups failed entirely, prefer polling inside the time window so local
    # live tracking still works rather than silently missing games.
    if all(result is None for result in scoreboard_results):
        logger.warning("Falling back to time-window-only live polling because scoreboard lookups failed.")
        return True

    return False


def _extract_score_map(game: Dict[str, Any]) -> Dict[str, int]:
    """Map team name to current score from a scores payload."""
    mapping: Dict[str, int] = {}
    for entry in game.get("scores") or []:
        name = entry.get("name") or entry.get("team") or entry.get("participant")
        if not name:
            continue
        mapping[str(name)] = _coerce_int(
            entry.get("score") or entry.get("points") or entry.get("value"),
            default=0,
        ) or 0
    return mapping


def _extract_status_text(game: Dict[str, Any]) -> str:
    """Flatten any status/clock fields into one uppercase string."""
    parts: List[str] = []
    for key in (
        "status",
        "clock",
        "time_remaining",
        "timeRemaining",
        "display_clock",
        "quarter",
        "period",
        "current_period",
    ):
        value = game.get(key)
        if isinstance(value, dict):
            parts.extend(str(v) for v in value.values() if v not in (None, ""))
        elif value not in (None, ""):
            parts.append(str(value))
    return " ".join(parts).upper()


def _is_completed(game: Dict[str, Any]) -> bool:
    """Return True when the payload represents a finished game."""
    if bool(game.get("completed")):
        return True

    status_text = _extract_status_text(game)
    return "FINAL" in status_text or "FT" in status_text


def _parse_clock_string(value: Any) -> Optional[int]:
    """Parse MM:SS style clock strings into seconds."""
    if value in (None, ""):
        return None

    text = str(value).strip()
    if ":" not in text:
        return None

    minutes_str, seconds_str = text.split(":", 1)
    try:
        return (int(minutes_str) * 60) + int(seconds_str)
    except ValueError:
        return None


def _format_clock(seconds_remaining: int) -> str:
    """Format seconds into MM:SS."""
    seconds_remaining = max(0, int(seconds_remaining))
    minutes, seconds = divmod(seconds_remaining, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _estimate_seconds_remaining(
    commence_time: Optional[datetime],
    now_utc: datetime,
    completed: bool,
) -> int:
    """Estimate remaining game seconds when the API omits the live clock."""
    if completed:
        return 0
    if commence_time is None:
        return FULL_GAME_SECONDS
    if now_utc <= commence_time:
        return FULL_GAME_SECONDS

    elapsed = max(0.0, (now_utc - commence_time).total_seconds())
    progress = min(elapsed / ESTIMATED_BROADCAST_SECONDS, 1.0)
    return max(0, int(round(FULL_GAME_SECONDS * (1.0 - progress))))


def _normalize_quarter_label(value: Any) -> Optional[str]:
    """Standardize quarter/period labels into Q1..Q4 / OT."""
    if value in (None, ""):
        return None

    text = str(value).strip().upper()
    if text.startswith("Q") or text.startswith("OT"):
        return text

    numeric = _coerce_int(value)
    if numeric is None:
        if text in {"HALF", "HALFTIME"}:
            return "HALF"
        return text
    if numeric <= 4:
        return f"Q{numeric}"
    return "OT"


def _derive_clock_snapshot(seconds_remaining: int) -> Dict[str, Any]:
    """Infer a period label and period clock from total game seconds remaining."""
    if seconds_remaining <= 0:
        return {
            "quarter": "FINAL",
            "time_remaining_str": "00:00",
            "seconds_remaining": 0,
        }

    regulation_remaining = min(int(seconds_remaining), FULL_GAME_SECONDS)
    elapsed = FULL_GAME_SECONDS - regulation_remaining
    period_index = min(3, elapsed // (12 * 60))
    period_elapsed = elapsed - (period_index * 12 * 60)
    period_remaining = max(0, (12 * 60) - int(period_elapsed))
    return {
        "quarter": f"Q{int(period_index) + 1}",
        "time_remaining_str": _format_clock(period_remaining),
        "seconds_remaining": regulation_remaining,
    }


def _extract_clock_snapshot(
    game: Dict[str, Any],
    commence_time: Optional[datetime],
    now_utc: datetime,
    completed: bool,
) -> Dict[str, Any]:
    """Build a quarter/clock/remaining-seconds snapshot from the live feed."""
    if completed:
        return {
            "quarter": "FINAL",
            "time_remaining_str": "00:00",
            "seconds_remaining": 0,
        }

    quarter = _normalize_quarter_label(
        game.get("quarter") or game.get("period") or game.get("current_period")
    )
    time_remaining_str = (
        game.get("time_remaining")
        or game.get("timeRemaining")
        or game.get("clock")
        or game.get("display_clock")
    )
    seconds_remaining = _coerce_int(
        game.get("seconds_remaining")
        or game.get("clock_seconds_remaining")
        or game.get("time_remaining_seconds")
    )

    if seconds_remaining is None and time_remaining_str:
        period_clock_seconds = _parse_clock_string(time_remaining_str)
        if period_clock_seconds is not None and quarter:
            quarter_number = _coerce_int(str(quarter).replace("Q", ""))
            if quarter_number is not None and 1 <= quarter_number <= 4:
                seconds_remaining = ((4 - quarter_number) * 12 * 60) + period_clock_seconds
            elif str(quarter).startswith("OT"):
                seconds_remaining = period_clock_seconds

    if seconds_remaining is None:
        seconds_remaining = _estimate_seconds_remaining(commence_time, now_utc, completed)

    derived = _derive_clock_snapshot(seconds_remaining)
    if quarter is None:
        quarter = derived["quarter"]
    if not time_remaining_str:
        time_remaining_str = derived["time_remaining_str"]

    return {
        "quarter": quarter,
        "time_remaining_str": str(time_remaining_str),
        "seconds_remaining": int(seconds_remaining),
    }


def _is_game_in_progress(game: Dict[str, Any], now_utc: datetime) -> bool:
    """Return True when a game appears live/in-progress."""
    if _is_completed(game):
        return False

    status_text = _extract_status_text(game)
    if any(marker in status_text for marker in ("LIVE", "IN PROGRESS", "Q1", "Q2", "Q3", "Q4", "OT", "HALF")):
        return True

    commence_time = _parse_iso_datetime(game.get("commence_time"))
    if commence_time is None:
        return any((_extract_score_map(game)).values())

    if now_utc < commence_time - timedelta(minutes=10):
        return False
    if now_utc > commence_time + timedelta(hours=5):
        return False
    if any((_extract_score_map(game)).values()):
        return True
    return now_utc >= commence_time


def _build_state_snapshot(game: Dict[str, Any], now_utc: datetime) -> Optional[Dict[str, Any]]:
    """Convert one scores payload into a DB-ready snapshot."""
    completed = _is_completed(game)
    in_progress = _is_game_in_progress(game, now_utc)
    if not completed and not in_progress:
        return None

    home_team = str(game.get("home_team") or "")
    away_team = str(game.get("away_team") or "")
    game_id = str(game.get("id") or "")
    if not all((game_id, home_team, away_team)):
        return None

    score_map = _extract_score_map(game)
    commence_time = _parse_iso_datetime(game.get("commence_time"))
    last_updated = (
        _parse_iso_datetime(game.get("last_update"))
        or _parse_iso_datetime(game.get("last_updated"))
        or now_utc
    )
    clock_snapshot = _extract_clock_snapshot(game, commence_time, now_utc, completed)

    return {
        "game_id": game_id,
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": game.get("commence_time"),
        "home_score": score_map.get(home_team, _coerce_int(game.get("home_score"), 0) or 0),
        "away_score": score_map.get(away_team, _coerce_int(game.get("away_score"), 0) or 0),
        "quarter": clock_snapshot["quarter"],
        "time_remaining_str": clock_snapshot["time_remaining_str"],
        "seconds_remaining": clock_snapshot["seconds_remaining"],
        "live_home_price": None,
        "live_home_point": None,
        "last_updated": last_updated.isoformat(),
    }


def _fetch_scores() -> List[Dict[str, Any]]:
    """Fetch the latest scoreboard state from The Odds API."""
    return _request_json(
        f"/sports/{SPORT}/scores",
        {
            "daysFrom": 1,
            "dateFormat": "iso",
        },
    )


def _fetch_live_odds(game_ids: List[str]) -> Dict[str, Dict[str, Optional[float]]]:
    """Fetch live moneyline/spread data for active games only."""
    if not game_ids:
        return {}

    games = _request_json(
        f"/sports/{SPORT}/odds",
        {
            "regions": REGIONS,
            "markets": LIVE_MARKETS,
            "bookmakers": TARGET_BOOKMAKER,
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "eventIds": ",".join(game_ids),
        },
    )

    parsed: Dict[str, Dict[str, Optional[float]]] = {}
    for game in games:
        game_id = str(game.get("id") or "")
        home_team = str(game.get("home_team") or "")
        if not game_id or not home_team:
            continue

        bookmakers = game.get("bookmakers") or []
        if not bookmakers:
            parsed[game_id] = {"live_home_price": None, "live_home_point": None}
            continue

        bookmaker = next((b for b in bookmakers if b.get("key") == TARGET_BOOKMAKER), bookmakers[0])
        home_price: Optional[float] = None
        home_point: Optional[float] = None

        for market in bookmaker.get("markets") or []:
            market_key = market.get("key")
            for outcome in market.get("outcomes") or []:
                if outcome.get("name") != home_team:
                    continue
                if market_key == "h2h":
                    home_price = _coerce_float(outcome.get("price"))
                elif market_key == "spreads":
                    home_point = _coerce_float(outcome.get("point"))

        parsed[game_id] = {
            "live_home_price": home_price,
            "live_home_point": home_point,
        }

    return parsed


def _upsert_live_snapshots(rows: Iterable[Dict[str, Any]]) -> int:
    """Upsert a set of live snapshots into SQLite."""
    conn = get_db()
    written = 0
    try:
        for row in rows:
            conn.execute(
                """
                INSERT INTO live_game_state (
                    game_id, home_team, away_team, commence_time, home_score, away_score,
                    quarter, time_remaining_str, seconds_remaining, live_home_price,
                    live_home_point, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    home_team = excluded.home_team,
                    away_team = excluded.away_team,
                    commence_time = excluded.commence_time,
                    home_score = excluded.home_score,
                    away_score = excluded.away_score,
                    quarter = excluded.quarter,
                    time_remaining_str = excluded.time_remaining_str,
                    seconds_remaining = excluded.seconds_remaining,
                    live_home_price = excluded.live_home_price,
                    live_home_point = excluded.live_home_point,
                    last_updated = excluded.last_updated
                """,
                (
                    row["game_id"],
                    row["home_team"],
                    row["away_team"],
                    row.get("commence_time"),
                    row["home_score"],
                    row["away_score"],
                    row.get("quarter"),
                    row.get("time_remaining_str"),
                    row.get("seconds_remaining"),
                    row.get("live_home_price"),
                    row.get("live_home_point"),
                    row.get("last_updated"),
                ),
            )
            written += 1
        conn.commit()
    finally:
        conn.close()
    return written


def fetch_live_scores_and_odds() -> List[Dict[str, Any]]:
    """Fetch live scoreboard data, attach live odds where available, and store snapshots."""
    now_utc = datetime.now(timezone.utc)
    score_games = _fetch_scores()
    if not score_games:
        return []

    snapshots = [snapshot for game in score_games if (snapshot := _build_state_snapshot(game, now_utc))]
    active_game_ids = [row["game_id"] for row in snapshots if int(row.get("seconds_remaining") or 0) > 0]
    live_odds = _fetch_live_odds(active_game_ids) if active_game_ids else {}

    for snapshot in snapshots:
        odds = live_odds.get(snapshot["game_id"])
        if not odds:
            continue
        snapshot["live_home_price"] = odds.get("live_home_price")
        snapshot["live_home_point"] = odds.get("live_home_point")

    if snapshots:
        _upsert_live_snapshots(snapshots)

    return [row for row in snapshots if int(row.get("seconds_remaining") or 0) > 0]


def poll_live_games(skip_window_check: bool = False) -> int:
    """Scheduler wrapper for live polling with a fast-fail when nothing is active."""
    if not skip_window_check and not are_games_currently_active():
        logger.info("Live polling skipped: outside active NBA window or no games scheduled.")
        return 0

    active_games = fetch_live_scores_and_odds()
    if not active_games:
        logger.info("Live polling skipped: no active NBA games detected.")
        return 0

    logger.info("Stored live snapshots for %s active NBA games.", len(active_games))
    return len(active_games)
