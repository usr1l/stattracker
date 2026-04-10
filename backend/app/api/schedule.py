from __future__ import annotations

"""Schedule endpoints for simple slate views."""

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request
from nba_api.stats.static import teams as nba_teams

from app.logger import get_logger
from app.services.scoreboard import get_live_boxscore_payload, get_live_scoreboard_payload, get_scoreboard_data_frames

bp = Blueprint("schedule", __name__, url_prefix="/api/schedule")
EASTERN = ZoneInfo("America/New_York")
logger = get_logger(__name__)
TEAM_BY_ID = {int(team["id"]): team for team in nba_teams.get_teams()}
TEAM_LOGO_URL_TEMPLATE = "https://cdn.nba.com/logos/nba/{team_id}/global/L/logo.svg"
LIVE_CLOCK_PATTERN = re.compile(r"^PT(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+(?:\.\d+)?)S)?$")
LIVE_SCOREBOARD_PREVIOUS_DAY_GRACE_HOURS = 6


class LiveScoreboardDateMismatch(LookupError):
    """Raised when the live CDN returns a different schedule date than requested."""

    def __init__(self, requested_date: str, live_date: str | None):
        self.requested_date = requested_date
        self.live_date = live_date
        message = f"NBA live scoreboard returned {live_date or 'unknown'} instead of {requested_date}."
        super().__init__(message)


def _team_logo_url(team_id: int) -> str:
    return TEAM_LOGO_URL_TEMPLATE.format(team_id=team_id)


def _normalize_text(value) -> str:
    return " ".join(str(value or "").split())


def _is_missing(value) -> bool:
    return value is None or value == "" or value != value


def _coerce_int(value):
    if _is_missing(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def _coerce_float(value):
    if _is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_percentage(value):
    parsed = _coerce_float(value)
    if parsed is None:
        return None
    return f"{parsed * 100:.1f}%"


def _parse_iso_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _row_for_game(df, game_id: str):
    if df.empty or "GAME_ID" not in df.columns:
        return None
    matches = df[df["GAME_ID"].astype(str) == str(game_id)]
    if matches.empty:
        return None
    return matches.iloc[0]


def _rows_for_game(df, game_id: str) -> dict[int, dict]:
    if df.empty or "GAME_ID" not in df.columns:
        return {}

    matches = df[df["GAME_ID"].astype(str) == str(game_id)]
    rows: dict[int, dict] = {}
    for _, row in matches.iterrows():
        team_id = _coerce_int(row.get("TEAM_ID"))
        if team_id is None:
            continue
        rows[team_id] = row.to_dict()
    return rows


def _leader_entry(name, value):
    if _is_missing(name) or _is_missing(value):
        return None
    return {
        "name": str(name),
        "value": _coerce_float(value),
    }


def _team_payload(team_id: int, line_row: dict | None, leader_row: dict | None) -> dict:
    team = TEAM_BY_ID.get(team_id, {})
    abbreviation = str(team.get("abbreviation") or (line_row or {}).get("TEAM_ABBREVIATION") or "")
    fallback_name = " ".join(
        part for part in [str((line_row or {}).get("TEAM_CITY_NAME") or "").strip(), str((line_row or {}).get("TEAM_NAME") or "").strip()] if part
    ).strip()

    leaders = {
        "points": _leader_entry((leader_row or {}).get("PTS_PLAYER_NAME"), (leader_row or {}).get("PTS")),
        "rebounds": _leader_entry((leader_row or {}).get("REB_PLAYER_NAME"), (leader_row or {}).get("REB")),
        "assists": _leader_entry((leader_row or {}).get("AST_PLAYER_NAME"), (leader_row or {}).get("AST")),
    }
    if not any(leaders.values()):
        leaders = None

    return {
        "team_id": team_id,
        "abbreviation": abbreviation,
        "name": str(team.get("full_name") or fallback_name or abbreviation),
        "logo_url": _team_logo_url(team_id),
        "score": _coerce_int((line_row or {}).get("PTS")),
        "record": None if _is_missing((line_row or {}).get("TEAM_WINS_LOSSES")) else str((line_row or {}).get("TEAM_WINS_LOSSES")),
        "leaders": leaders,
    }


def _parse_live_game_clock(value) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    if ":" in text:
        return text

    match = LIVE_CLOCK_PATTERN.match(text)
    if not match:
        return text

    minutes = int(match.group("minutes") or 0)
    seconds = int(float(match.group("seconds") or 0))
    if seconds >= 60:
        minutes += seconds // 60
        seconds %= 60
    return f"{minutes}:{seconds:02d}"


def _live_team_period_map(team_payload: dict | None) -> dict[int, int | None]:
    periods = (team_payload or {}).get("periods") or []
    if not isinstance(periods, list):
        return {}

    scores: dict[int, int | None] = {}
    for period in periods:
        if not isinstance(period, dict):
            continue
        period_number = _coerce_int(period.get("period"))
        if period_number is None:
            continue
        scores[period_number] = _coerce_int(period.get("score"))
    return scores


def _live_game_has_points_data(game: dict) -> bool:
    for team_key in ("homeTeam", "awayTeam"):
        period_map = _live_team_period_map(game.get(team_key))
        if period_map:
            return True
    return False


def _live_team_name(team_payload: dict | None) -> str:
    team_id = _coerce_int((team_payload or {}).get("teamId"))
    fallback_name = " ".join(
        part
        for part in [
            str((team_payload or {}).get("teamCity") or "").strip(),
            str((team_payload or {}).get("teamName") or "").strip(),
        ]
        if part
    ).strip()
    team = TEAM_BY_ID.get(team_id or -1, {})
    return str(team.get("full_name") or fallback_name or (team_payload or {}).get("teamTricode") or "")


def _live_team_record(team_payload: dict | None) -> str | None:
    wins = _coerce_int((team_payload or {}).get("wins"))
    losses = _coerce_int((team_payload or {}).get("losses"))
    if wins is None or losses is None:
        return None
    return f"{wins}-{losses}"


def _live_leader_entry(leader_payload: dict | None, stat_key: str) -> dict | None:
    if not isinstance(leader_payload, dict):
        return None

    name = leader_payload.get("name")
    value = _coerce_float(leader_payload.get(stat_key))
    if _is_missing(name) or value is None:
        return None
    return {
        "name": str(name),
        "value": value,
    }


def _live_team_leaders(leader_payload: dict | None) -> dict | None:
    leaders = {
        "points": _live_leader_entry(leader_payload, "points"),
        "rebounds": _live_leader_entry(leader_payload, "rebounds"),
        "assists": _live_leader_entry(leader_payload, "assists"),
    }
    if not any(leaders.values()):
        return None
    return leaders


def _derive_live_game_state(game: dict) -> str:
    status_id = _coerce_int(game.get("gameStatus"))
    status_text = _normalize_text(game.get("gameStatusText")).upper()
    live_period = _coerce_int(game.get("period")) or 0

    if status_id == 3 or "FINAL" in status_text:
        return "final"
    if status_id == 2:
        return "live"
    if live_period > 0:
        return "live"
    if _live_game_has_points_data(game):
        return "live"
    return "pre"


def _derive_live_status_display(game: dict, state: str) -> str:
    status_text = _normalize_text(game.get("gameStatusText"))
    live_period = _coerce_int(game.get("period")) or 0
    live_clock = _parse_live_game_clock(game.get("gameClock"))

    if state == "final":
        return status_text or "Final"
    if state == "live":
        if status_text and not _status_text_is_scheduled(status_text):
            return status_text
        if live_period > 0 and live_clock:
            return f"Q{live_period} {live_clock}"
        return "Live"
    return status_text or "Scheduled"


def _build_live_status_debug(game: dict, state: str) -> dict:
    return {
        "game_status_id": _coerce_int(game.get("gameStatus")),
        "game_status_text": _normalize_text(game.get("gameStatusText")) or None,
        "live_period": _coerce_int(game.get("period")),
        "live_pc_time": _parse_live_game_clock(game.get("gameClock")),
        "live_period_time_bcast": _derive_live_status_display(game, state),
        "has_linescore": bool(_live_team_period_map(game.get("homeTeam")) or _live_team_period_map(game.get("awayTeam"))),
        "has_points_data": _live_game_has_points_data(game),
    }


def _live_team_payload(team_payload: dict | None, leader_payload: dict | None, state: str, has_points_data: bool) -> dict:
    team_id = _coerce_int((team_payload or {}).get("teamId")) or 0
    team = TEAM_BY_ID.get(team_id, {})
    abbreviation = str((team_payload or {}).get("teamTricode") or team.get("abbreviation") or "")
    score = _coerce_int((team_payload or {}).get("score"))
    if state == "pre" and not has_points_data:
        score = None

    return {
        "team_id": team_id,
        "abbreviation": abbreviation,
        "name": _live_team_name(team_payload),
        "logo_url": _team_logo_url(team_id) if team_id else "",
        "score": score,
        "record": _live_team_record(team_payload),
        "leaders": _live_team_leaders(leader_payload),
    }


def _status_text_is_scheduled(value) -> bool:
    status_text = _normalize_text(value).upper()
    if not status_text:
        return False
    return status_text == "SCHEDULED" or any(
        token in status_text for token in (" AM", " PM", " ET", " CT", " MT", " PT")
    )


def _line_rows_have_points_data(line_rows: dict[int, dict]) -> bool:
    for row in line_rows.values():
        if _coerce_int(row.get("PTS")) is not None:
            return True
        for period_number in range(1, 5):
            if _coerce_int(row.get(f"PTS_QTR{period_number}")) is not None:
                return True
        for overtime_number in range(1, 11):
            if _coerce_int(row.get(f"PTS_OT{overtime_number}")) is not None:
                return True
    return False


def _build_status_debug(header_row, line_rows: dict[int, dict]) -> dict:
    return {
        "game_status_id": _coerce_int(header_row.get("GAME_STATUS_ID")),
        "game_status_text": _normalize_text(header_row.get("GAME_STATUS_TEXT")) or None,
        "live_period": _coerce_int(header_row.get("LIVE_PERIOD")),
        "live_pc_time": _normalize_text(header_row.get("LIVE_PC_TIME")) or None,
        "live_period_time_bcast": _normalize_text(header_row.get("LIVE_PERIOD_TIME_BCAST")) or None,
        "has_linescore": bool(line_rows),
        "has_points_data": _line_rows_have_points_data(line_rows),
    }


def _derive_game_state(header_row, line_rows: dict[int, dict]) -> str:
    status_id = _coerce_int(header_row.get("GAME_STATUS_ID"))
    status_text = _normalize_text(header_row.get("GAME_STATUS_TEXT")).upper()
    live_period = _coerce_int(header_row.get("LIVE_PERIOD")) or 0
    live_banner = _normalize_text(header_row.get("LIVE_PERIOD_TIME_BCAST")).upper()

    if status_id == 3 or "FINAL" in status_text or live_banner.startswith("FINAL"):
        return "final"
    if status_id == 2:
        return "live"
    if live_period > 0:
        return "live"
    if live_banner and not live_banner.startswith("Q0"):
        return "live"
    if _line_rows_have_points_data(line_rows):
        return "live"
    return "pre"


def _derive_status_display(header_row, state: str) -> str:
    status_text = _normalize_text(header_row.get("GAME_STATUS_TEXT"))
    live_period = _coerce_int(header_row.get("LIVE_PERIOD")) or 0
    live_clock = _normalize_text(header_row.get("LIVE_PC_TIME"))
    live_banner = _normalize_text(header_row.get("LIVE_PERIOD_TIME_BCAST"))

    if state == "final":
        return status_text or "Final"
    if state == "live":
        if live_banner and not live_banner.upper().startswith("Q0"):
            return live_banner
        if live_period > 0 and live_clock:
            return f"Q{live_period} {live_clock}"
        if status_text and not _status_text_is_scheduled(status_text):
            return status_text
        return "Live"
    return status_text or "Scheduled"


def _log_scoreboard_state(scope: str, date_str: str, game_id: str, fetched_at: str, state: str, status_debug: dict) -> None:
    logger.info(
        "scoreboard_state scope=%s date=%s game_id=%s fetched_at=%s state=%s debug=%s",
        scope,
        date_str,
        game_id,
        fetched_at,
        state,
        status_debug,
    )


def _build_linescore(state: str, home_line: dict | None, away_line: dict | None) -> list[dict]:
    if not home_line and not away_line:
        return []

    periods: list[dict] = []
    for period_number in range(1, 5):
        key = f"PTS_QTR{period_number}"
        periods.append(
            {
                "label": f"Q{period_number}",
                "home": _coerce_int((home_line or {}).get(key)),
                "away": _coerce_int((away_line or {}).get(key)),
            }
        )

    for overtime_number in range(1, 11):
        key = f"PTS_OT{overtime_number}"
        home_value = _coerce_int((home_line or {}).get(key))
        away_value = _coerce_int((away_line or {}).get(key))
        if home_value is None and away_value is None:
            continue
        periods.append(
            {
                "label": f"OT{overtime_number}",
                "home": home_value,
                "away": away_value,
            }
        )

    if state == "pre" and not any(period["home"] is not None or period["away"] is not None for period in periods):
        return []

    periods.append(
        {
            "label": "T",
            "home": _coerce_int((home_line or {}).get("PTS")),
            "away": _coerce_int((away_line or {}).get("PTS")),
        }
    )
    return periods


def _build_team_stats(home_line: dict | None, away_line: dict | None) -> list[dict]:
    stat_rows: list[dict] = []
    definitions = [
        ("FG%", "FG_PCT", _format_percentage),
        ("3PT%", "FG3_PCT", _format_percentage),
        ("FT%", "FT_PCT", _format_percentage),
        ("REB", "REB", _coerce_int),
        ("AST", "AST", _coerce_int),
        ("TOV", "TOV", _coerce_int),
    ]

    for label, key, formatter in definitions:
        home_value = formatter((home_line or {}).get(key))
        away_value = formatter((away_line or {}).get(key))
        if home_value is None and away_value is None:
            continue
        stat_rows.append(
            {
                "label": label,
                "home": home_value,
                "away": away_value,
            }
        )

    return stat_rows


def _build_last_meeting(last_meeting_row) -> dict | None:
    if last_meeting_row is None:
        return None

    home_abbreviation = str(last_meeting_row.get("LAST_GAME_HOME_TEAM_ABBREVIATION") or "").strip()
    away_abbreviation = str(last_meeting_row.get("LAST_GAME_VISITOR_TEAM_CITY1") or "").strip()
    home_points = _coerce_int(last_meeting_row.get("LAST_GAME_HOME_TEAM_POINTS"))
    away_points = _coerce_int(last_meeting_row.get("LAST_GAME_VISITOR_TEAM_POINTS"))

    return {
        "date": str(last_meeting_row.get("LAST_GAME_DATE_EST") or ""),
        "summary": " ".join(
            part
            for part in [
                home_abbreviation if home_abbreviation else None,
                str(home_points) if home_points is not None else None,
                "-" if home_points is not None or away_points is not None else None,
                away_abbreviation if away_abbreviation else None,
                str(away_points) if away_points is not None else None,
            ]
            if part is not None
        ).strip(),
    }


def _build_series(series_row) -> dict | None:
    if series_row is None:
        return None

    return {
        "leader": None if _is_missing(series_row.get("SERIES_LEADER")) else str(series_row.get("SERIES_LEADER")),
        "home_wins": _coerce_int(series_row.get("HOME_TEAM_WINS")),
        "home_losses": _coerce_int(series_row.get("HOME_TEAM_LOSSES")),
    }


def _load_live_scoreboard_games(date_str: str) -> list[dict]:
    payload = get_live_scoreboard_payload()
    scoreboard = payload.get("scoreboard") or {}
    if not isinstance(scoreboard, dict):
        raise ValueError("NBA live scoreboard payload is missing the scoreboard object.")

    live_date = str(scoreboard.get("gameDate") or "")
    if live_date != date_str:
        raise LiveScoreboardDateMismatch(date_str, live_date or None)

    games = scoreboard.get("games") or []
    if not isinstance(games, list):
        raise ValueError("NBA live scoreboard payload is missing its games list.")
    return games


def _build_live_linescore(state: str, game: dict) -> list[dict]:
    home_periods = _live_team_period_map(game.get("homeTeam"))
    away_periods = _live_team_period_map(game.get("awayTeam"))
    if state == "pre" and not home_periods and not away_periods:
        return []

    period_numbers = sorted(set(home_periods) | set(away_periods))
    regulation_periods = _coerce_int(game.get("regulationPeriods")) or 4
    periods: list[dict] = []

    for period_number in period_numbers:
        if period_number <= regulation_periods:
            label = f"Q{period_number}"
        else:
            label = f"OT{period_number - regulation_periods}"
        periods.append(
            {
                "label": label,
                "home": home_periods.get(period_number),
                "away": away_periods.get(period_number),
            }
        )

    periods.append(
        {
            "label": "T",
            "home": _coerce_int((game.get("homeTeam") or {}).get("score")),
            "away": _coerce_int((game.get("awayTeam") or {}).get("score")),
        }
    )
    return periods


def _load_live_schedule(date_str: str) -> list[dict]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    games: list[dict] = []

    for game in _load_live_scoreboard_games(date_str):
        if not isinstance(game, dict):
            continue

        game_id = str(game.get("gameId") or "").strip()
        if not game_id:
            continue

        away_team = game.get("awayTeam") or {}
        home_team = game.get("homeTeam") or {}
        away_team_id = _coerce_int(away_team.get("teamId"))
        home_team_id = _coerce_int(home_team.get("teamId"))
        away_abbr = str(away_team.get("teamTricode") or TEAM_BY_ID.get(away_team_id or -1, {}).get("abbreviation") or "")
        home_abbr = str(home_team.get("teamTricode") or TEAM_BY_ID.get(home_team_id or -1, {}).get("abbreviation") or "")
        if not away_abbr or not home_abbr:
            continue

        state = _derive_live_game_state(game)
        status_debug = _build_live_status_debug(game, state)
        _log_scoreboard_state("today", date_str, game_id, fetched_at, state, status_debug)

        games.append(
            {
                "game_id": game_id,
                "date": date_str,
                "status": _normalize_text(game.get("gameStatusText")),
                "status_display": _derive_live_status_display(game, state),
                "state": state,
                "scoreboard_fetched_at": fetched_at,
                "home_team": home_abbr,
                "away_team": away_abbr,
                "home_name": _live_team_name(home_team),
                "away_name": _live_team_name(away_team),
                "home_logo_url": _team_logo_url(home_team_id) if home_team_id else "",
                "away_logo_url": _team_logo_url(away_team_id) if away_team_id else "",
            }
        )

    return games


def _load_live_game_detail(date_str: str, game_id: str) -> dict:
    fetched_at = datetime.now(timezone.utc).isoformat()
    payload = get_live_boxscore_payload(game_id)
    selected_game = payload.get("game") or {}
    if not isinstance(selected_game, dict) or not selected_game:
        raise LookupError(f"No NBA live boxscore game found for game_id={game_id}.")

    state = _derive_live_game_state(selected_game)
    status_debug = _build_live_status_debug(selected_game, state)
    has_points_data = status_debug["has_points_data"]
    away_team = selected_game.get("awayTeam") or {}
    home_team = selected_game.get("homeTeam") or {}
    arena = selected_game.get("arena") or {}

    _log_scoreboard_state("detail", date_str, game_id, fetched_at, state, status_debug)

    return {
        "game_id": str(game_id),
        "date": date_str,
        "status": _normalize_text(selected_game.get("gameStatusText")),
        "status_display": _derive_live_status_display(selected_game, state),
        "state": state,
        "scoreboard_fetched_at": fetched_at,
        "status_debug": status_debug,
        "arena": None if _is_missing(arena.get("arenaName")) else str(arena.get("arenaName")),
        "broadcasts": {
            "national": None,
            "home": None,
            "away": None,
        },
        "home_team": _live_team_payload(home_team, None, state, has_points_data),
        "away_team": _live_team_payload(away_team, None, state, has_points_data),
        "linescore": _build_live_linescore(state, selected_game),
        "team_stats": [],
        "last_meeting": None,
        "series": None,
    }


def _load_stats_schedule(date_str: str) -> list[dict[str, str]]:
    target = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d/%Y")
    data_frames = get_scoreboard_data_frames(target, ["GameHeader", "LineScore"])
    header_df = data_frames["GameHeader"]
    line_score_df = data_frames["LineScore"]
    fetched_at = datetime.now(timezone.utc).isoformat()

    games: list[dict[str, str]] = []
    for _, row in header_df.iterrows():
        game_id = str(row["GAME_ID"])
        line_rows = _rows_for_game(line_score_df, game_id)
        state = _derive_game_state(row, line_rows)
        status_debug = _build_status_debug(row, line_rows)

        home_team_id = int(row["HOME_TEAM_ID"])
        away_team_id = int(row["VISITOR_TEAM_ID"])
        home_team = TEAM_BY_ID.get(home_team_id, {})
        away_team = TEAM_BY_ID.get(away_team_id, {})
        home_abbr = str(home_team.get("abbreviation") or "")
        away_abbr = str(away_team.get("abbreviation") or "")
        if not home_abbr or not away_abbr:
            continue

        _log_scoreboard_state("today", date_str, game_id, fetched_at, state, status_debug)
        games.append(
            {
                "game_id": game_id,
                "date": date_str,
                "status": _normalize_text(row.get("GAME_STATUS_TEXT")),
                "status_display": _derive_status_display(row, state),
                "state": state,
                "scoreboard_fetched_at": fetched_at,
                "home_team": home_abbr,
                "away_team": away_abbr,
                "home_name": str(home_team.get("full_name") or home_abbr),
                "away_name": str(away_team.get("full_name") or away_abbr),
                "home_logo_url": _team_logo_url(home_team_id),
                "away_logo_url": _team_logo_url(away_team_id),
            }
        )

    return games


def _load_stats_game_detail(date_str: str, game_id: str) -> dict:
    target = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d/%Y")
    data_frames = get_scoreboard_data_frames(
        target,
        ["GameHeader", "LineScore", "TeamLeaders", "LastMeeting", "SeriesStandings"],
    )
    header_df = data_frames["GameHeader"]
    line_score_df = data_frames["LineScore"]
    leaders_df = data_frames["TeamLeaders"]
    last_meeting_df = data_frames["LastMeeting"]
    series_df = data_frames["SeriesStandings"]
    fetched_at = datetime.now(timezone.utc).isoformat()

    header_row = _row_for_game(header_df, game_id)
    if header_row is None:
        raise LookupError(f"No NBA scoreboard game found for {date_str} and game_id={game_id}.")

    home_team_id = _coerce_int(header_row["HOME_TEAM_ID"])
    away_team_id = _coerce_int(header_row["VISITOR_TEAM_ID"])
    if home_team_id is None or away_team_id is None:
        raise LookupError(f"Incomplete scoreboard team data for game_id={game_id}.")

    line_rows = _rows_for_game(line_score_df, game_id)
    leader_rows = _rows_for_game(leaders_df, game_id)
    state = _derive_game_state(header_row, line_rows)
    status_debug = _build_status_debug(header_row, line_rows)

    home_line = line_rows.get(home_team_id)
    away_line = line_rows.get(away_team_id)
    _log_scoreboard_state("detail", date_str, game_id, fetched_at, state, status_debug)

    return {
        "game_id": str(game_id),
        "date": date_str,
        "status": _normalize_text(header_row.get("GAME_STATUS_TEXT")),
        "status_display": _derive_status_display(header_row, state),
        "state": state,
        "scoreboard_fetched_at": fetched_at,
        "status_debug": status_debug,
        "arena": None if _is_missing(header_row.get("ARENA_NAME")) else str(header_row.get("ARENA_NAME")),
        "broadcasts": {
            "national": None if _is_missing(header_row.get("NATL_TV_BROADCASTER_ABBREVIATION")) else str(header_row.get("NATL_TV_BROADCASTER_ABBREVIATION")),
            "home": None if _is_missing(header_row.get("HOME_TV_BROADCASTER_ABBREVIATION")) else str(header_row.get("HOME_TV_BROADCASTER_ABBREVIATION")),
            "away": None if _is_missing(header_row.get("AWAY_TV_BROADCASTER_ABBREVIATION")) else str(header_row.get("AWAY_TV_BROADCASTER_ABBREVIATION")),
        },
        "home_team": _team_payload(home_team_id, home_line, leader_rows.get(home_team_id)),
        "away_team": _team_payload(away_team_id, away_line, leader_rows.get(away_team_id)),
        "linescore": _build_linescore(state, home_line, away_line),
        "team_stats": _build_team_stats(home_line, away_line),
        "last_meeting": _build_last_meeting(_row_for_game(last_meeting_df, game_id)),
        "series": _build_series(_row_for_game(series_df, game_id)),
    }


def _load_schedule(date_str: str) -> list[dict]:
    today_str = datetime.now(EASTERN).date().isoformat()
    if date_str == today_str:
        try:
            return _load_live_schedule(date_str)
        except LiveScoreboardDateMismatch as exc:
            requested_date = _parse_iso_date(exc.requested_date)
            live_date = _parse_iso_date(exc.live_date)
            now_est = datetime.now(EASTERN)
            expected_previous_day_lag = (
                requested_date == now_est.date()
                and live_date == (requested_date - timedelta(days=1) if requested_date else None)
                and now_est.hour < LIVE_SCOREBOARD_PREVIOUS_DAY_GRACE_HOURS
            )
            if expected_previous_day_lag:
                logger.info(
                    "Falling back to stats.nba.com schedule for %s while the live CDN still reports %s during the overnight window.",
                    date_str,
                    exc.live_date,
                )
            else:
                logger.warning("Falling back to stats.nba.com schedule for %s after live CDN failure: %s", date_str, exc)
        except Exception as exc:
            logger.warning("Falling back to stats.nba.com schedule for %s after live CDN failure: %s", date_str, exc)
    return _load_stats_schedule(date_str)


def _load_game_detail(date_str: str, game_id: str) -> dict:
    try:
        return _load_live_game_detail(date_str, game_id)
    except Exception as exc:
        logger.warning(
            "Falling back to stats.nba.com detail for %s/%s after live boxscore failure: %s",
            date_str,
            game_id,
            exc,
        )
    return _load_stats_game_detail(date_str, game_id)


@bp.route("/today", methods=["GET"])
def get_today_schedule():
    """Return today's NBA slate using the Eastern schedule day."""
    date_str = datetime.now(EASTERN).date().isoformat()
    try:
        return jsonify(_load_schedule(date_str))
    except Exception as exc:
        return jsonify({"error": f"NBA scoreboard fetch failed for {date_str}: {exc}"}), 502


@bp.route("/games/<game_id>", methods=["GET"])
def get_game_detail(game_id):
    """Return one game's detail payload for the selected schedule date."""
    date_str = request.args.get("date") or datetime.now(EASTERN).date().isoformat()
    try:
        return jsonify(_load_game_detail(date_str, game_id))
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"NBA game detail fetch failed for {date_str}/{game_id}: {exc}"}), 502
