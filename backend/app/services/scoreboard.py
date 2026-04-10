"""Helpers for reading scoreboard data from nba_api safely."""

from __future__ import annotations

import pandas as pd
import requests
from nba_api.stats.endpoints import ScoreboardV2
from nba_api.stats.library.http import NBAStatsHTTP

LIVE_SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
LIVE_BOXSCORE_URL_TEMPLATE = "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"


def _coerce_data_frame(data_set: dict | None) -> pd.DataFrame:
    """Build a dataframe from a raw nba_api result set."""

    if not data_set:
        return pd.DataFrame()

    headers = data_set.get("headers") or []
    rows = data_set.get("data") or []
    return pd.DataFrame(rows, columns=headers)


def _fetch_scoreboard_data_sets(game_date: str) -> dict[str, dict]:
    """Return raw scoreboard result sets without forcing optional tables.

    `ScoreboardV2.load_response()` assumes the API always returns a `WinProbability`
    table and raises `KeyError` when that optional result set is missing. Pulling the
    raw response lets us read the stable `GameHeader` dataset directly.
    """

    return NBAStatsHTTP().send_api_request(
        endpoint=ScoreboardV2.endpoint,
        parameters={"DayOffset": 0, "GameDate": game_date, "LeagueID": "00"},
        timeout=30,
    ).get_data_sets()


def get_scoreboard_data_frame(game_date: str, data_set_name: str) -> pd.DataFrame:
    """Return one named scoreboard dataset for a MM/DD/YYYY date."""

    data_sets = _fetch_scoreboard_data_sets(game_date)
    return _coerce_data_frame(data_sets.get(data_set_name))


def get_scoreboard_data_frames(game_date: str, data_set_names: list[str]) -> dict[str, pd.DataFrame]:
    """Return multiple named scoreboard datasets from one API request."""

    data_sets = _fetch_scoreboard_data_sets(game_date)
    return {
        data_set_name: _coerce_data_frame(data_sets.get(data_set_name))
        for data_set_name in data_set_names
    }


def get_live_scoreboard_payload(timeout: int = 15) -> dict:
    """Return the NBA live scoreboard payload from the CDN endpoint."""

    response = requests.get(LIVE_SCOREBOARD_URL, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("NBA live scoreboard returned a non-object payload.")
    return payload


def get_live_boxscore_payload(game_id: str, timeout: int = 15) -> dict:
    """Return the NBA live boxscore payload for one game id."""

    response = requests.get(LIVE_BOXSCORE_URL_TEMPLATE.format(game_id=game_id), timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("NBA live boxscore returned a non-object payload.")
    return payload


def get_scoreboard_game_header(game_date: str) -> pd.DataFrame:
    """Return the scoreboard's game_header dataset for one MM/DD/YYYY date.

    nba_api can fail when iterating all returned datasets because some optional datasets
    arrive empty or with inconsistent headers. Reading the explicit game_header table avoids
    that failure mode while still giving us the schedule rows we need.
    """

    return get_scoreboard_data_frame(game_date, "GameHeader")
