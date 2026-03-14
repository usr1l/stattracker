"""Track NBA futures markets (championship, win totals) for macro surges."""
from typing import List, Dict, Any
import requests
import os
from datetime import datetime, timedelta

from market.db import get_db

FUTURES_SURGE_THRESHOLD_PCT = 0.15 # 15% probability shift

# Note: The Odds API futures endpoint requires specific parameters
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")

def fetch_and_store_futures(market_key: str = "outrights"):
    """Fetch futures and save to DB."""
    if not ODDS_API_KEY:
        return
        
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba_{market_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "outrights",
    }
    try:
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            return
            
        data = resp.json()
        if not data:
            return
            
        conn = get_db()
        # simplified parsing assuming DraftKings or similar primary book
        for event in data:
            bookmakers = event.get("bookmakers", [])
            if not bookmakers: continue
            outcomes = bookmakers[0]["markets"][0]["outcomes"]
            
            for oc in outcomes:
                team = oc["name"]
                price = oc["price"]
                
                conn.execute("""
                    INSERT INTO futures_history (market, team, price)
                    VALUES (?, ?, ?)
                """, (market_key, team, price))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Futures fetch error: {e}")


def detect_futures_surges():
    """Find teams whose futures odds have shortened significantly in the last week."""
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        teams = conn.execute("SELECT DISTINCT team FROM futures_history").fetchall()
        
        for row in teams:
            team = row["team"]
            old = conn.execute("""
                SELECT price FROM futures_history 
                WHERE team = ? AND timestamp >= ? 
                ORDER BY timestamp ASC LIMIT 1
            """, (team, cutoff)).fetchone()
            
            curr = conn.execute("""
                SELECT price FROM futures_history 
                WHERE team = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (team,)).fetchone()
            
            if old and curr:
                # Convert decimal odds to implied probability
                old_prob = 1 / old["price"]
                curr_prob = 1 / curr["price"]
                
                pct_change = (curr_prob - old_prob) / old_prob
                
                if pct_change >= FUTURES_SURGE_THRESHOLD_PCT:
                    desc = f"Championship odds surged! Implied prob increased {(pct_change*100):.1f}% (from {old['price']} to {curr['price']})"
                    
                    exists = conn.execute("""
                        SELECT id FROM market_signals 
                        WHERE team = ? AND signal_type = 'future_surge' 
                        AND timestamp > datetime('now', '-1 day')
                    """, (team,)).fetchone()
                    
                    if not exists:
                        conn.execute("""
                            INSERT INTO market_signals (signal_type, team, description, magnitude)
                            VALUES ('future_surge', ?, ?, ?)
                        """, (team, desc, pct_change))
        conn.commit()
    finally:
        conn.close()
