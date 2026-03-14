"""Detect sharp vs public money splits (stub for premium API data)."""
from market.db import get_db

VOLUME_DIVERGENCE_THRESHOLD = 15.0  # 15% diff between ticket% and handle%

def detect_sharp_volume(game_id: str, home_ticket_pct: float, home_handle_pct: float, home_team: str):
    """
    If 80% of tickets (public) are on home, but only 60% of handle (money) is on home, 
    the sharp money (20% diff) is heavily on the away team.
    """
    diff = home_ticket_pct - home_handle_pct
    
    if abs(diff) >= VOLUME_DIVERGENCE_THRESHOLD:
        favored_team = "AWAY" if diff > 0 else "HOME"
        desc = f"Sharp money on {favored_team}: {home_ticket_pct:.1f}% tickets vs {home_handle_pct:.1f}% handle on home."
        
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO market_signals (signal_type, game_id, team, description, magnitude)
                VALUES ('volume', ?, ?, ?, ?)
            """, (game_id, home_team, desc, abs(diff)))
            conn.commit()
        finally:
            conn.close()
