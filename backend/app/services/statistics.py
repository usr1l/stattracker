"""Statistics service - wraps get_statistics with caching."""
from typing import List, Optional, Union

import pandas as pd

from app.config import CACHE_TTL_GAMELOGS_HOURS, PREVIOUS_SEASONS
from app.cache import get_cached, make_gamelogs_key, set_cached


def _df_to_records(df: pd.DataFrame) -> List[dict]:
    """Convert DataFrame to JSON-serializable list of dicts."""
    return df.replace({pd.NA: None}).astype(object).to_dict(orient="records")


def get_player_career_stats(player_id: Union[int, str]) -> Optional[List[dict]]:
    """Get career stats for a player."""
    from get_statistics import NBAStats

    stats = NBAStats()
    try:
        df = stats.get_player_career_stats(int(player_id))
        return _df_to_records(df)
    except Exception:
        return None


def get_player_game_logs(
    player_id: Union[int, str],
    matchup: str = "",
    seasons: Optional[List[str]] = None,
    num_games: int = 20,
    home: bool = False,
    away: bool = False,
    ast: Optional[int] = None,
    reb: Optional[int] = None,
    pts: Optional[int] = None,
    stl: Optional[int] = None,
    blk: Optional[int] = None,
    pf: Optional[int] = None,
    threes_made: Optional[int] = None,
    triple_double: Optional[bool] = None,
    double_double: Optional[bool] = None,
    win: Optional[bool] = None,
) -> List[dict]:
    """Get filtered game logs for a player. Uses cache when possible."""
    seasons = seasons or PREVIOUS_SEASONS
    filters = {
        "matchup": matchup,
        "seasons": seasons,
        "num_games": num_games,
        "home": home,
        "away": away,
        "ast": ast,
        "reb": reb,
        "pts": pts,
        "stl": stl,
        "blk": blk,
        "pf": pf,
        "threes_made": threes_made,
        "triple_double": triple_double,
        "double_double": double_double,
        "win": win,
    }
    cache_key = make_gamelogs_key(player_id, **filters)
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    from get_statistics import NBAStats

    stats = NBAStats()
    try:
        df = stats.get_player_statistics(
            player_id=int(player_id),
            matchup=matchup,
            seasons=seasons,
            num_games=num_games,
            home=home,
            away=away,
            ast=ast,
            reb=reb,
            pts=pts,
            stl=stl,
            blk=blk,
            pf=pf,
            threes_made=threes_made,
            triple_double=triple_double,
            double_double=double_double,
            win=win,
        )
        records = _df_to_records(df)
        set_cached(cache_key, records, CACHE_TTL_GAMELOGS_HOURS)
        return records
    except Exception:
        return []
