"""SQLite schema and connection for market data."""
import sqlite3
from pathlib import Path

# Path: backend/instance/market.db
INSTANCE_PATH = Path(__file__).resolve().parent.parent / "instance"
MARKET_DB_PATH = INSTANCE_PATH / "market.db"


def get_db() -> sqlite3.Connection:
    """Get a connection to the market database."""
    INSTANCE_PATH.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(MARKET_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the market database schema."""
    conn = get_db()
    try:
        # Table for raw odds snapshots
        conn.execute("""
            CREATE TABLE IF NOT EXISTS odds_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                commence_time TEXT NOT NULL,
                bookmaker TEXT NOT NULL,
                market_type TEXT NOT NULL, -- 'h2h', 'spreads', 'totals'
                home_price REAL,
                away_price REAL,
                home_point REAL,
                away_point REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Index to query history for a specific game quickly
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_odds_game_id ON odds_history(game_id)"
        )

        # Table for detected surges/signals (line movement, volume, futures)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_type TEXT NOT NULL, -- 'line_movement', 'volume', 'future_surge'
                game_id TEXT, -- nullable for futures
                team TEXT,
                description TEXT NOT NULL,
                magnitude REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table for Futures
        conn.execute("""
            CREATE TABLE IF NOT EXISTS futures_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL, -- e.g., 'championship', 'win_total'
                team TEXT NOT NULL,
                price REAL NOT NULL,
                points REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

# Run init on import
init_db()
