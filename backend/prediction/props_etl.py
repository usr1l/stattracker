"""ETL jobs for advanced player props data."""
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from nba_api.stats.endpoints import CommonTeamRoster, commonplayerinfo, playergamelog
from nba_api.stats.static import teams

from market.db import get_db
from season import load_seasons

TRACKED_PROP_STATS = ("PTS", "REB", "AST")
BASELINE_WINDOW = 10
DEFAULT_POSITION = "SF"
POSITION_ALIASES = {
    "PG": "PG",
    "SG": "SG",
    "SF": "SF",
    "PF": "PF",
    "C": "C",
    "G": "PG",
    "F": "SF",
    "G-F": "SG",
    "F-G": "SF",
    "F-C": "PF",
    "C-F": "C",
}


def _normalize_position(raw_position: Any) -> str:
    """Collapse roster position labels into PG/SG/SF/PF/C."""
    if raw_position is None:
        return DEFAULT_POSITION

    cleaned = str(raw_position).strip().upper()
    if not cleaned:
        return DEFAULT_POSITION
    if cleaned in POSITION_ALIASES:
        return POSITION_ALIASES[cleaned]

    for part in cleaned.replace("/", "-").split("-"):
        part = part.strip()
        if part in POSITION_ALIASES:
            return POSITION_ALIASES[part]

    return DEFAULT_POSITION


def _lookup_player_position(player_id: int) -> str:
    """Fallback position lookup when roster data is missing a usable position."""
    try:
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id).get_data_frames()[0]
    except Exception:
        return DEFAULT_POSITION
    if info.empty:
        return DEFAULT_POSITION
    return _normalize_position(info.iloc[0].get("POSITION"))


def _parse_minutes(value: Any) -> float:
    """Convert a minutes value into decimal minutes."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return 0.0
    if ":" not in text:
        try:
            return float(text)
        except ValueError:
            return 0.0

    minutes, seconds = text.split(":", 1)
    try:
        return float(minutes) + (float(seconds) / 60.0)
    except ValueError:
        return 0.0


def _extract_opponent_team(matchup: Any) -> str:
    """Extract the opposing team abbreviation from a matchup string."""
    if matchup is None:
        return ""
    parts = str(matchup).strip().upper().split()
    if not parts:
        return ""
    return parts[-1]


def _fetch_player_logs(player_id: int, season: str) -> pd.DataFrame:
    """Fetch a player's regular-season logs for the given season."""
    try:
        df = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star="Regular Season",
        ).get_data_frames()[0]
    except TypeError:
        df = playergamelog.PlayerGameLog(player_id=player_id, season=season).get_data_frames()[0]

    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["PLAYER_ID"] = int(player_id)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="coerce")
    return df.sort_values("GAME_DATE", ascending=False).reset_index(drop=True)


def _collect_player_logs(player_ids: Iterable[int], season: str) -> Dict[int, pd.DataFrame]:
    """Fetch current-season logs for a set of active players."""
    logs_by_player: Dict[int, pd.DataFrame] = {}
    for player_id in player_ids:
        df = _fetch_player_logs(int(player_id), season)
        if not df.empty:
            logs_by_player[int(player_id)] = df
    return logs_by_player


def _load_position_map(season: str) -> Dict[int, Dict[str, str]]:
    """Load the player position mapping from SQLite, refreshing it if needed."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT player_id, team_abbr, position FROM player_positions"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        refresh_player_positions(season=season)
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT player_id, team_abbr, position FROM player_positions"
            ).fetchall()
        finally:
            conn.close()

    return {
        int(row["player_id"]): {
            "team_abbr": str(row["team_abbr"]),
            "position": str(row["position"]),
        }
        for row in rows
    }


def _write_player_positions(rows: List[Tuple[int, str, str, Optional[str]]]) -> None:
    """Replace the player_positions table with the latest roster snapshot."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM player_positions")
        conn.executemany(
            """
            INSERT INTO player_positions (player_id, team_abbr, position, player_name)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _write_defense_matrix(rows: List[Tuple[str, str, str, float, int]]) -> None:
    """Replace the opponent defense matrix with the latest aggregates."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM opponent_defense_matrix")
        conn.executemany(
            """
            INSERT INTO opponent_defense_matrix (team_abbr, position, stat, modifier, sample_size)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def _write_player_baselines(rows: List[Tuple[int, str, float, float, int]]) -> None:
    """Replace the player baselines table with the latest recent-form rates."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM player_baselines")
        conn.executemany(
            """
            INSERT INTO player_baselines (player_id, stat, per_minute_rate, projected_minutes, sample_size)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def refresh_player_positions(season: Optional[str] = None) -> Dict[str, Any]:
    """Fetch current team rosters and persist a normalized primary position per player."""
    current_season, _ = load_seasons()
    season = season or current_season

    teams_data = teams.get_teams()
    rows: List[Tuple[int, str, str, Optional[str]]] = []

    for team in teams_data:
        try:
            roster_df = CommonTeamRoster(team_id=team["id"], season=season).get_data_frames()[0]
        except TypeError:
            roster_df = CommonTeamRoster(team_id=team["id"]).get_data_frames()[0]
        if roster_df.empty:
            continue

        for record in roster_df.to_dict(orient="records"):
            player_id = record.get("PLAYER_ID")
            if player_id is None:
                continue

            position = _normalize_position(record.get("POSITION"))
            if position == DEFAULT_POSITION and not record.get("POSITION"):
                position = _lookup_player_position(int(player_id))

            rows.append(
                (
                    int(player_id),
                    str(team["abbreviation"]).upper(),
                    position,
                    record.get("PLAYER"),
                )
            )

    _write_player_positions(rows)
    return {
        "season": season,
        "teams_processed": len(teams_data),
        "players_upserted": len(rows),
    }


def refresh_defense_matrix(
    season: Optional[str] = None,
    position_map: Optional[Dict[int, Dict[str, str]]] = None,
    logs_by_player: Optional[Dict[int, pd.DataFrame]] = None,
) -> Dict[str, Any]:
    """Calculate team-vs-position defensive modifiers for points, rebounds, and assists."""
    current_season, _ = load_seasons()
    season = season or current_season
    position_map = position_map or _load_position_map(season)
    logs_by_player = logs_by_player or _collect_player_logs(position_map.keys(), season)

    frames = []
    for player_id, df in logs_by_player.items():
        if df.empty:
            continue
        working = df.copy()
        working["PLAYER_ID"] = int(player_id)
        frames.append(working[["PLAYER_ID", "MATCHUP", "PTS", "REB", "AST"]])

    if not frames:
        _write_defense_matrix([])
        return {
            "season": season,
            "teams_indexed": 0,
            "rows_written": 0,
        }

    logs = pd.concat(frames, ignore_index=True)
    logs["position"] = logs["PLAYER_ID"].map(
        lambda player_id: position_map.get(int(player_id), {}).get("position")
    )
    logs["opponent_team"] = logs["MATCHUP"].apply(_extract_opponent_team)
    logs = logs[
        logs["position"].notna()
        & logs["opponent_team"].fillna("").astype(str).str.fullmatch(r"[A-Z]{3}")
    ]

    rows: List[Tuple[str, str, str, float, int]] = []
    indexed_teams = set()

    for stat in TRACKED_PROP_STATS:
        stat_logs = logs[["opponent_team", "position", stat]].dropna()
        if stat_logs.empty:
            continue

        league_position_avg = stat_logs.groupby("position")[stat].mean().to_dict()
        grouped = (
            stat_logs.groupby(["opponent_team", "position"])[stat]
            .agg(["mean", "count"])
            .reset_index()
        )

        for record in grouped.to_dict(orient="records"):
            baseline = float(league_position_avg.get(record["position"], 0.0))
            modifier = float(record["mean"]) / baseline if baseline > 0 else 1.0
            team_abbr = str(record["opponent_team"]).upper()
            indexed_teams.add(team_abbr)
            rows.append(
                (
                    team_abbr,
                    str(record["position"]),
                    stat,
                    modifier,
                    int(record["count"]),
                )
            )

    _write_defense_matrix(rows)
    return {
        "season": season,
        "teams_indexed": len(indexed_teams),
        "rows_written": len(rows),
    }


def refresh_player_baselines(
    season: Optional[str] = None,
    position_map: Optional[Dict[int, Dict[str, str]]] = None,
    logs_by_player: Optional[Dict[int, pd.DataFrame]] = None,
    window: int = BASELINE_WINDOW,
) -> Dict[str, Any]:
    """Calculate recent per-minute prop baselines and projected minutes."""
    current_season, _ = load_seasons()
    season = season or current_season
    position_map = position_map or _load_position_map(season)
    logs_by_player = logs_by_player or _collect_player_logs(position_map.keys(), season)

    rows: List[Tuple[int, str, float, float, int]] = []

    for player_id, df in logs_by_player.items():
        recent = df.head(int(window)).copy()
        if recent.empty:
            continue

        minutes = recent["MIN"].apply(_parse_minutes)
        total_minutes = float(minutes.sum())
        if total_minutes <= 0:
            continue

        projected_minutes = float(minutes.mean())
        sample_size = int(len(recent))

        for stat in TRACKED_PROP_STATS:
            stat_total = pd.to_numeric(recent[stat], errors="coerce").fillna(0.0).sum()
            per_minute_rate = float(stat_total) / total_minutes
            rows.append(
                (
                    int(player_id),
                    stat,
                    per_minute_rate,
                    projected_minutes,
                    sample_size,
                )
            )

    _write_player_baselines(rows)
    return {
        "season": season,
        "players_indexed": len({row[0] for row in rows}),
        "rows_written": len(rows),
    }


def refresh_all_props_data(season: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Run the advanced props ETL sequence with shared roster and log context."""
    current_season, _ = load_seasons()
    season = season or current_season

    positions = refresh_player_positions(season=season)
    position_map = _load_position_map(season)
    logs_by_player = _collect_player_logs(position_map.keys(), season)

    defense = refresh_defense_matrix(
        season=season,
        position_map=position_map,
        logs_by_player=logs_by_player,
    )
    baselines = refresh_player_baselines(
        season=season,
        position_map=position_map,
        logs_by_player=logs_by_player,
    )

    return {
        "player_positions": positions,
        "opponent_defense_matrix": defense,
        "player_baselines": baselines,
    }
