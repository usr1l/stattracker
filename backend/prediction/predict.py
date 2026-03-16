"""Pre-game prediction interface combining all signals."""
from typing import Any, Dict, Mapping, Optional

from prediction.features import build_game_features
from prediction.model import predict
from prediction.trends import get_team_trends
from market.db import get_db


def predict_game(
    home_team: str,
    away_team: str,
    game_date: str,
    game_id: str = None,
    weights: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """Generate a full pre-game prediction report with ensemble breakdowns."""
    # 1. Base statistical features & ML model prediction
    features = build_game_features(home_team, away_team, game_date)
    projections = predict(features, weights=weights)
    
    # 2. Add trend warnings
    home_trends = get_team_trends(home_team)
    away_trends = get_team_trends(away_team)
    
    # 3. Add market signals (if game_id provided)
    market_signals = []
    if game_id:
        conn = get_db()
        try:
            # Get any signals generated in the last 24h for this game
            rows = conn.execute("""
                SELECT signal_type, team, description 
                FROM market_signals 
                WHERE game_id = ? AND timestamp >= datetime('now', '-1 day')
            """, (game_id,)).fetchall()
            
            for r in rows:
                market_signals.append({
                    "type": r["signal_type"],
                    "team": r["team"],
                    "desc": r["description"]
                })
        finally:
            conn.close()
            
    return {
        "matchup": {
            "home": home_team,
            "away": away_team,
            "date": game_date
        },
        "projections": projections,
        "features_snapshot": features,
        "trends": {
            "home": home_trends.get("surge_flags", []),
            "away": away_trends.get("surge_flags", []),
        },
        "market_signals": market_signals
    }
