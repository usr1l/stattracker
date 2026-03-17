"""Track line movement and detect sharp market action."""
from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.logger import get_logger
from market.db import get_db

MOVEMENT_SURGE_THRESHOLD = 2.5  # points
MOVEMENT_SURGE_HOURS = 4
logger = get_logger(__name__)


def get_game_line_history(game_id: str, market_type: str = "spreads") -> List[Dict[str, Any]]:
    """Get the chronological line history for a specific game and market."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT timestamp, home_price, away_price, home_point, away_point
            FROM odds_history
            WHERE game_id = ? AND market_type = ?
            ORDER BY timestamp ASC
        """, (game_id, market_type)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def detect_surges() -> None:
    """Analyze recent odds history to find sudden line movement (sharp action)."""
    conn = get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=MOVEMENT_SURGE_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
        
        # We look at games happening in the future
        games = conn.execute("""
            SELECT DISTINCT game_id, home_team, away_team 
            FROM odds_history 
            WHERE commence_time > datetime('now')
        """).fetchall()
        
        for game in games:
            game_id = game["game_id"]
            
            for mtype in ["spreads", "totals"]:
                # Get oldest line in the window
                open_line = conn.execute("""
                    SELECT home_point, away_point, timestamp 
                    FROM odds_history 
                    WHERE game_id = ? AND market_type = ? AND timestamp >= ?
                    ORDER BY timestamp ASC LIMIT 1
                """, (game_id, mtype, cutoff)).fetchone()
                
                # Get newest line
                current_line = conn.execute("""
                    SELECT home_point, away_point, timestamp 
                    FROM odds_history 
                    WHERE game_id = ? AND market_type = ?
                    ORDER BY timestamp DESC LIMIT 1
                """, (game_id, mtype)).fetchone()
                
                if open_line and current_line and open_line["home_point"] is not None and current_line["home_point"] is not None:
                    delta = current_line["home_point"] - open_line["home_point"]
                    
                    if abs(delta) >= MOVEMENT_SURGE_THRESHOLD:
                        desc = f"{mtype.capitalize()} moved {delta:+.1f} points since {open_line['timestamp']} (Current: {current_line['home_point']})"
                        
                        # Store signal if we haven't recently
                        exists = conn.execute("""
                            SELECT id FROM market_signals 
                            WHERE game_id = ? AND signal_type = 'line_movement' 
                            AND timestamp > datetime('now', '-1 hour')
                        """, (game_id,)).fetchone()
                        
                        if not exists:
                            conn.execute("""
                                INSERT INTO market_signals (signal_type, game_id, team, description, magnitude)
                                VALUES ('line_movement', ?, ?, ?, ?)
                            """, (game_id, game["home_team"], desc, abs(delta)))
                            logger.info(
                                "Detected surge for %s vs %s: %s",
                                game["home_team"],
                                game["away_team"],
                                desc,
                            )
        conn.commit()
    finally:
        conn.close()
