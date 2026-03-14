"""Trend and surge detection based on rolling statistics."""
from typing import Dict, Any, List

def calculate_rolling_trends(team_id: int, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate rolling 5/10/20 game trends and momentum scores."""
    if not logs or len(logs) < 20:
        return {}
        
    # Assume logs are sorted latest to earliest
    # In a full implementation, we compute team-level Net Rating here
    # For Phase 1 stub, we return placeholder values that will eventually feed the ML model
    
    # Momentum = (Last 5 Net Rating - Season Net Rating) / Season Standard Deviation
    momentum_score = 1.25 # Stub value
    
    trends = {
        "l5_net_rating": 5.4,
        "l10_net_rating": 3.2,
        "season_net_rating": 1.1,
        "momentum_zscore": momentum_score,
        "streak_w": 3,
        "streak_l": 0,
    }
    
    flags = []
    if momentum_score > 1.5:
        flags.append("HOT_STREAK: Surging well above season average (+1.5 std dev)")
    elif momentum_score < -1.5:
        flags.append("COLD_STREAK: Slumping below season average (-1.5 std dev)")
        
    trends["surge_flags"] = flags
    return trends
    
def get_team_trends(team_name: str) -> Dict[str, Any]:
    """Retrieve current trends for a team (stub)."""
    return calculate_rolling_trends(0, [{"dummy": True}]*20)
