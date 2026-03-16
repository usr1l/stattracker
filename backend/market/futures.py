import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests

from market.db import get_db

FUTURES_SURGE_THRESHOLD_PCT = 0.15  # 15% probability shift

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com/v4"
SPORT = "basketball_nba"


def fetch_and_store_futures(market_key: str = "outrights") -> None:
    """Fetch futures and save to DB."""
    if not ODDS_API_KEY:
        return

    # Futures are requested via the standard sport key + markets=outrights.
    url = f"{BASE_URL}/sports/{SPORT}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": market_key,
        "oddsFormat": "decimal",
    }
    conn = None
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()

        data: List[Dict[str, Any]] = resp.json()
        if not data:
            return

        conn = get_db()
        # Simplified parsing: take first bookmaker that offers outrights.
        for event in data:
            bookmakers = event.get("bookmakers", [])
            if not bookmakers:
                continue

            futures_market = None
            for bookmaker in bookmakers:
                for market in bookmaker.get("markets", []):
                    if market.get("key") == market_key:
                        futures_market = market
                        break
                if futures_market:
                    break

            if not futures_market:
                continue

            outcomes = futures_market.get("outcomes", [])
            for oc in outcomes:
                team = oc["name"]
                price = oc["price"]
                conn.execute("""
                    INSERT INTO futures_history (market, team, price)
                    VALUES (?, ?, ?)
                """, (market_key, team, price))
        conn.commit()
    except Exception as e:
        print(f"Futures fetch error: {e}")
    finally:
        if conn is not None:
            conn.close()


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
