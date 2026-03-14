"""Backtesting engine for evaluating prediction accuracy, ROI, and CLV."""
import math
from typing import List, Dict, Any


def decimal_odds_to_prob(decimal_odds: float) -> float:
    if decimal_odds <= 0: return 0.0
    return 1.0 / decimal_odds


def calculate_kelly_criterion(prob: float, decimal_odds: float, fraction: float = 0.25) -> float:
    """
    f = (bp - q) / b
    b = decimal_odds - 1 (net odds)
    p = prob of winning
    q = 1 - p (prob of losing)
    """
    if prob <= 0 or prob >= 1 or decimal_odds <= 1.0:
        return 0.0
        
    b = decimal_odds - 1.0
    p = prob
    q = 1.0 - p
    
    kelly_f = (b * p - q) / b
    
    # Only bet if edge is positive
    if kelly_f <= 0:
        return 0.0
        
    return kelly_f * fraction


def run_backtest(games: List[Dict[str, Any]], starting_bankroll: float = 10000.0) -> Dict[str, Any]:
    """
    Run backtest on a historical list of games with closing odds.
    Expected format per game:
    {
      "date": "...",
      "home_team": "...", "away_team": "...",
      "home_score": 110, "away_score": 105,
      "home_odds": 1.5, "away_odds": 2.6,   # Closing decimal odds
      "model_home_prob": 0.70               # Model prediction
    }
    """
    bankroll = starting_bankroll
    wins = 0
    losses = 0
    total_bets = 0
    brier_sum = 0.0
    
    max_drawdown = 0.0
    peak_bankroll = bankroll
    
    for g in games:
        # Determine actual result
        home_won = g["home_score"] > g["away_score"]
        actual_result = 1.0 if home_won else 0.0
        
        model_prob = g["model_home_prob"]
        
        # Brier score: (forecast - actual)^2
        brier_sum += (model_prob - actual_result)**2
        
        # Find betting edge
        home_implied = decimal_odds_to_prob(g["home_odds"])
        away_implied = decimal_odds_to_prob(g["away_odds"])
        
        bet_size = 0.0
        placed_bet_on_home = None
        
        # Simple rule: bet if model prob > implied prob
        if model_prob > home_implied:
            placed_bet_on_home = True
            bet_size = calculate_kelly_criterion(model_prob, g["home_odds"], fraction=0.25) * bankroll
        elif (1.0 - model_prob) > away_implied:
            placed_bet_on_home = False
            bet_size = calculate_kelly_criterion(1.0 - model_prob, g["away_odds"], fraction=0.25) * bankroll
            
        if bet_size > 0:
            total_bets += 1
            if placed_bet_on_home is True:
                if home_won:
                    profit = bet_size * (g["home_odds"] - 1.0)
                    bankroll += profit
                    wins += 1
                else:
                    bankroll -= bet_size
                    losses += 1
            else: # Bet on away
                if not home_won:
                    profit = bet_size * (g["away_odds"] - 1.0)
                    bankroll += profit
                    wins += 1
                else:
                    bankroll -= bet_size
                    losses += 1
                    
        if bankroll > peak_bankroll:
            peak_bankroll = bankroll
        drawdown = peak_bankroll - bankroll
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    brier = brier_sum / len(games) if len(games) > 0 else 0
    roi = ((bankroll - starting_bankroll) / starting_bankroll) * 100.0
    
    return {
        "games_processed": len(games),
        "total_bets": total_bets,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / total_bets) if total_bets > 0 else 0,
        "starting_bankroll": starting_bankroll,
        "ending_bankroll": bankroll,
        "roi_percent": roi,
        "max_drawdown": max_drawdown,
        "brier_score": brier
    }
