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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_game_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season TEXT NOT NULL,
                game_id TEXT NOT NULL,
                game_date TEXT NOT NULL,
                team_abbr TEXT NOT NULL,
                matchup TEXT,
                wl TEXT,
                pts REAL,
                opp_pts REAL,
                pace REAL,
                efg_pct REAL,
                tov_pct REAL,
                off_rating REAL,
                def_rating REAL,
                net_rating REAL,
                source TEXT DEFAULT 'TeamGameLogs',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(season, game_id, team_abbr)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_team_logs_team_date ON team_game_logs(team_abbr, game_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_team_logs_season ON team_game_logs(season)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_positions (
                player_id INTEGER PRIMARY KEY,
                team_abbr TEXT NOT NULL,
                position TEXT NOT NULL,
                player_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_positions_team ON player_positions(team_abbr)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS opponent_defense_matrix (
                team_abbr TEXT NOT NULL,
                position TEXT NOT NULL,
                stat TEXT NOT NULL,
                modifier REAL NOT NULL,
                sample_size INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_abbr, position, stat)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_opp_defense_lookup ON opponent_defense_matrix(team_abbr, position, stat)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_baselines (
                player_id INTEGER NOT NULL,
                stat TEXT NOT NULL,
                per_minute_rate REAL NOT NULL,
                projected_minutes REAL NOT NULL,
                sample_size INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, stat)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_baselines_player ON player_baselines(player_id)"
        )
        conn.commit()
    finally:
        conn.close()

# Run init on import
init_db()
