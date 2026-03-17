"""Client for The Odds API (https://the-odds-api.com)."""
import os
from typing import Any, Dict, List

import requests

from app.logger import get_logger
from market.db import get_db

ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com/v4"
SPORT = "basketball_nba"
REGIONS = "us"
MARKETS = "h2h,spreads,totals"
logger = get_logger(__name__)


def get_live_odds() -> List[Dict[str, Any]]:
    """Fetch live and upcoming NBA odds."""
    if not ODDS_API_KEY:
        logger.warning("ODDS_API_KEY not set. Skipping odds fetch.")
        return []
        
    url = f"{BASE_URL}/sports/{SPORT}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": "decimal",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error("Error fetching odds: %s", e)
        return []


def store_odds_snapshot(games: List[Dict[str, Any]], target_bookmaker: str = "draftkings") -> None:
    """Parse API response and store the snapshot in SQLite."""
    if not games:
        return
        
    conn = get_db()
    try:
        for game in games:
            game_id = game["id"]
            home_team = game["home_team"]
            away_team = game["away_team"]
            commence_time = game["commence_time"]
            
            # Find target bookmaker (or fallback to first available)
            bookmakers = game.get("bookmakers", [])
            if not bookmakers:
                continue
                
            book = next((b for b in bookmakers if b["key"] == target_bookmaker), bookmakers[0])
            book_title = book["title"]
            
            for market in book.get("markets", []):
                mtype = market["key"]
                outcomes = market["outcomes"]
                
                # Default nulls
                home_price, away_price, home_point, away_point = None, None, None, None
                
                if mtype == "h2h":
                    for oc in outcomes:
                        if oc["name"] == home_team:
                            home_price = oc["price"]
                        elif oc["name"] == away_team:
                            away_price = oc["price"]
                
                elif mtype == "spreads":
                    for oc in outcomes:
                        if oc["name"] == home_team:
                            home_price = oc["price"]
                            home_point = oc.get("point")
                        elif oc["name"] == away_team:
                            away_price = oc["price"]
                            away_point = oc.get("point")
                            
                elif mtype == "totals":
                    for oc in outcomes:
                        if oc["name"] == "Over":
                            home_price = oc["price"]  # using home for Over
                            home_point = oc.get("point")
                        elif oc["name"] == "Under":
                            away_price = oc["price"]  # using away for Under
                            away_point = oc.get("point")
                
                conn.execute("""
                    INSERT INTO odds_history (
                        game_id, home_team, away_team, commence_time, bookmaker, 
                        market_type, home_price, away_price, home_point, away_point
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (game_id, home_team, away_team, commence_time, book_title, mtype,
                      home_price, away_price, home_point, away_point))
        conn.commit()
    finally:
        conn.close()


def poll_and_store_odds():
    """Wrapper to be called by scheduler."""
    games = get_live_odds()
    store_odds_snapshot(games)
    logger.info("Stored odds snapshot for %s games.", len(games))
