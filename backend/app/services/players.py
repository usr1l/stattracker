"""Players service - wraps get_players with caching."""
from typing import List, Optional, Union

import pandas as pd
from app.config import (
    CACHE_TTL_PLAYERS_HOURS,
    PLAYERS_CSV_PATH,
    PROJECT_ROOT,
)
from app.cache import get_cached, set_cached

CACHE_KEY_PLAYERS = "players_list"


def _ensure_players_csv_dir() -> None:
    """Ensure players_csv directory exists."""
    PLAYERS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)


def _df_to_records(df: pd.DataFrame) -> List[dict]:
    """Convert DataFrame to JSON-serializable list of dicts."""
    return df.replace({pd.NA: None}).astype(object).to_dict(orient="records")


def get_all_players() -> List[dict]:
    """Get all NBA players. Uses cache; on miss fetches from API and caches."""
    cached = get_cached(CACHE_KEY_PLAYERS)
    if cached is not None:
        return cached

    from get_players import get_nba_players_csv, NBA

    _ensure_players_csv_dir()
    get_nba_players_csv()
    nba = NBA(str(PLAYERS_CSV_PATH))
    df = nba.df
    records = _df_to_records(df)
    set_cached(CACHE_KEY_PLAYERS, records, CACHE_TTL_PLAYERS_HOURS)
    return records


def search_players(query: str) -> List[dict]:
    """Search players by name (partial, case-insensitive)."""
    players = get_all_players()
    q = query.lower()
    return [p for p in players if q in str(p.get("DISPLAY_FIRST_LAST", "")).lower()]


def get_player_by_id(player_id: Union[int, str]) -> Optional[dict]:
    """Get a single player by ID."""
    players = get_all_players()
    pid = int(player_id)
    for p in players:
        if p.get("PERSON_ID") == pid:
            return p
    return None


def get_teams() -> List[dict]:
    """Get all NBA teams: id, full_name, abbreviation."""
    from nba_api.stats.static import teams

    teams_data = teams.get_teams()
    return [
        {"id": t["id"], "full_name": t["full_name"], "abbreviation": t["abbreviation"]}
        for t in teams_data
    ]


def get_team_roster(team_name: str) -> Optional[List[dict]]:
    """Get roster for a team by name (e.g. 'celtics'). Returns {player_name: player_id} or None."""
    from get_players import NBA, get_nba_teams

    players = get_all_players()
    nba = NBA(str(PLAYERS_CSV_PATH))
    teams = get_nba_teams()
    team_name_lower = team_name.lower()
    if team_name_lower not in teams:
        return None
    try:
        roster = nba.get_players_by_team(team_name_lower)
        return [{"player_id": v, "player_name": k} for k, v in roster.items()]
    except (KeyError, TypeError):
        return None
