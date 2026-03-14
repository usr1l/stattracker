"""Analysis service - wraps analyze_tables."""
from typing import List, Optional, Union

import pandas as pd

from app.services.statistics import get_player_game_logs


def _records_to_df(records: List[dict]) -> pd.DataFrame:
    """Convert list of dicts to DataFrame."""
    return pd.DataFrame(records)


def get_cat_probability(
    logs: Optional[List[dict]] = None,
    player_id: Optional[Union[int, str]] = None,
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
) -> dict:
    """Calculate probability of hitting a stat line. Provide logs or player_id."""
    from analyze_tables import Analysis

    if logs is None and player_id is None:
        return {"error": "Provide logs or player_id"}
    if logs is None:
        logs = get_player_game_logs(player_id)
    df = _records_to_df(logs)
    if df.empty:
        return {"error": "No games found"}

    analysis = Analysis()
    try:
        cats, hit, total, pct = analysis.get_cats_probability(
            df,
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
        return {"criteria": cats, "hit": int(hit), "total": int(total), "percentage": pct}
    except Exception as e:
        return {"error": str(e)}


def get_combination_probability(
    player_ids: List[Union[int, str]],
    players: List[dict],
    combine: str = "all",
) -> dict:
    """Calculate same-game combo probability for multiple players."""
    from analyze_tables import Analysis

    if len(player_ids) != len(players):
        return {"error": "Players and criteria mismatch"}
    logs_list = [get_player_game_logs(pid) for pid in player_ids]
    dfs = [_records_to_df(logs) for logs in logs_list]
    if any(df.empty for df in dfs):
        return {"error": "No games found for one or more players"}

    analysis = Analysis()
    try:
        result = analysis.get_combination_probability(
            logs=dfs, players=players, combine=combine
        )
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


def get_probability_table_combos(
    player_ids: List[Union[int, str]],
    cats: Optional[List[str]] = None,
    graph_size: int = 31,
) -> dict:
    """Get probability table for combined stats across multiple players."""
    from analyze_tables import Analysis, CATS

    if len(player_ids) < 2:
        return {"error": "Insufficient entries (need at least 2 players)"}
    cats = cats or list(CATS)
    logs_list = [get_player_game_logs(pid) for pid in player_ids]
    dfs = [_records_to_df(logs) for logs in logs_list]
    if any(df.empty for df in dfs):
        return {"error": "No games found for one or more players"}

    analysis = Analysis()
    try:
        table = analysis.get_probability_table_combos(
            logs=dfs, cats=cats, graph_size=graph_size
        )
        if isinstance(table, str):
            return {"error": table}
        return {"table": table.to_dict()}
    except Exception as e:
        return {"error": str(e)}


def get_cat_averages(logs: List[dict], cats: Optional[List[str]] = None) -> dict:
    """Get average stats for a set of game logs."""
    from analyze_tables import Analysis, CATS

    df = _records_to_df(logs)
    if df.empty:
        return {}
    analysis = Analysis()
    cats = cats or list(CATS)
    avgs = analysis.get_cat_averages(df, cats=cats)
    return {k: float(v) for k, v in avgs.items()}
