"""Trend and surge detection based on rolling team statistics."""
from typing import Any, Dict, List

import pandas as pd

from market.db import get_db
from prediction.team_stats import get_team_rolling_stats


def calculate_rolling_trends(team_abbr: str, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate rolling net-rating trends and momentum z-score."""
    if not logs:
        return {}

    df = pd.DataFrame(logs)
    if "net_rating" not in df.columns:
        return {}

    df["net_rating"] = pd.to_numeric(df["net_rating"], errors="coerce")
    df = df.dropna(subset=["net_rating"])
    if df.empty:
        return {}

    season_net = float(df["net_rating"].mean())
    season_std = float(df["net_rating"].std(ddof=0)) if len(df) > 1 else 0.0
    l5_net = float(df.head(5)["net_rating"].mean()) if len(df) >= 1 else season_net
    l10_net = float(df.head(10)["net_rating"].mean()) if len(df) >= 1 else season_net
    momentum = 0.0 if season_std <= 1e-9 else (l5_net - season_net) / season_std

    streak_w = 0
    streak_l = 0
    for result in df.get("wl", []):
        if result == "W" and streak_l == 0:
            streak_w += 1
        elif result == "L" and streak_w == 0:
            streak_l += 1
        else:
            break

    flags: List[str] = []
    if momentum >= 1.5:
        flags.append("HOT_STREAK: Surging well above season average (+1.5 std dev)")
    elif momentum <= -1.5:
        flags.append("COLD_STREAK: Slumping below season average (-1.5 std dev)")

    if abs(l5_net - l10_net) >= 5.0:
        flags.append("RECENT_SHIFT: Last-5 form diverges from last-10 baseline")

    # Surface a synced snapshot from team_stats module used by feature engineering.
    today_stats = get_team_rolling_stats(team_abbr, "2999-12-31", window=10)

    return {
        "l5_net_rating": l5_net,
        "l10_net_rating": l10_net,
        "season_net_rating": season_net,
        "momentum_zscore": float(momentum),
        "streak_w": streak_w,
        "streak_l": streak_l,
        "rolling_snapshot": today_stats,
        "surge_flags": flags,
    }


def get_team_trends(team_name: str) -> Dict[str, Any]:
    """Retrieve latest trend stats for a team abbreviation."""
    team_abbr = team_name.upper()
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT game_date, wl, net_rating, off_rating, def_rating
            FROM team_game_logs
            WHERE team_abbr = ?
            ORDER BY game_date DESC
            LIMIT 30
            """,
            (team_abbr,),
        ).fetchall()
    finally:
        conn.close()

    return calculate_rolling_trends(team_abbr, [dict(r) for r in rows])
