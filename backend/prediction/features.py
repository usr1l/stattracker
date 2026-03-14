"""Feature engineering pipeline for prediction models."""
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, Any

from app.services.statistics import get_player_game_logs
from prediction.elo import load_elo, get_team_elo

# Helper functions for feature generation

def calculate_rest_days(team_id: int, game_date: datetime, logs: pd.DataFrame) -> int:
    """Calculate days of rest since last game."""
    if logs.empty:
        return 7 # Default to rested
        
    logs['GAME_DATE'] = pd.to_datetime(logs['GAME_DATE'])
    past_games = logs[logs['GAME_DATE'] < game_date].sort_values(by='GAME_DATE', ascending=False)
    
    if past_games.empty:
        return 7
        
    last_game_date = past_games.iloc[0]['GAME_DATE']
    diff = (game_date - last_game_date).days
    return diff


def calculate_team_rolling_stats(team_id: int, game_date: datetime, window: int = 10) -> Dict[str, float]:
    """Calculate rolling offensive/defensive metrics for a team."""
    # Stub: Normally this would query a team-level box score cache
    # For now, we return mock/baseline values to ensure pipeline runs
    return {
        "off_rating": 115.0,
        "def_rating": 115.0,
        "net_rating": 0.0,
        "pace": 98.0,
        "efg_pct": 0.54,
        "tov_pct": 0.14,
        "oreb_pct": 0.28,
        "ft_rate": 0.20,
    }


def build_game_features(home_team: str, away_team: str, game_date: str) -> Dict[str, Any]:
    """
    Build a feature vector for a specific upcoming game.
    home_team/away_team: string abbreviations or full names matching ELO dict
    game_date: YYYY-MM-DD
    """
    dt = datetime.strptime(game_date, "%Y-%m-%d")
    
    # 1. ELO Features
    ratings = load_elo()
    home_elo = get_team_elo(home_team, ratings)
    away_elo = get_team_elo(away_team, ratings)
    elo_diff = (home_elo + 100) - away_elo # Include home adv
    
    # 2. Team Stats (Rolling 10 games)
    # Stub: real implementation queries TeamGameLogs from nba_api
    home_stats = calculate_team_rolling_stats(0, dt, 10)
    away_stats = calculate_team_rolling_stats(0, dt, 10)
    
    net_rating_diff = home_stats["net_rating"] - away_stats["net_rating"]
    
    # 3. Schedule Features
    # Stub: real implementation queries team schedule
    home_rest = 2
    away_rest = 1
    
    return {
        "home_elo": home_elo,
        "away_elo": away_elo,
        "elo_diff": elo_diff,
        "home_net_rating_l10": home_stats["net_rating"],
        "away_net_rating_l10": away_stats["net_rating"],
        "net_rating_diff": net_rating_diff,
        "home_rest_days": home_rest,
        "away_rest_days": away_rest,
        "home_b2b": 1 if home_rest == 1 else 0,
        "away_b2b": 1 if away_rest == 1 else 0,
    }
