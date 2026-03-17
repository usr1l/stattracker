"""SQLite schema and connection for market data."""
import os
import sqlite3
from pathlib import Path

# Path: backend/instance/market.db
INSTANCE_PATH = Path(__file__).resolve().parent.parent / "instance"
MARKET_DB_PATH = INSTANCE_PATH / "market.db"


def get_database_url() -> str:
    """Return the configured database URL."""
    return os.environ.get("DATABASE_URL", f"sqlite:///{MARKET_DB_PATH}")


def _resolve_sqlite_path() -> Path:
    """Resolve a sqlite:/// URL into a filesystem path for legacy raw-SQL helpers."""
    db_url = get_database_url()
    if not db_url.startswith("sqlite:///"):
        raise RuntimeError(
            "Legacy raw SQL helpers only support sqlite DATABASE_URL values. "
            "Apply the ORM query migration before switching the runtime database engine."
        )

    path_text = db_url.removeprefix("sqlite:///")
    resolved = Path(path_text)
    if not resolved.is_absolute():
        resolved = (Path.cwd() / resolved).resolve()
    return resolved


def get_db() -> sqlite3.Connection:
    """Get a connection to the market database."""
    db_path = _resolve_sqlite_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the market database schema."""
    if not get_database_url().startswith("sqlite:///"):
        return

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historical_odds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season TEXT,
                game_id TEXT,
                game_date TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                bookmaker TEXT NOT NULL,
                home_open_price REAL,
                away_open_price REAL,
                home_close_price REAL,
                away_close_price REAL,
                home_open_spread REAL,
                away_open_spread REAL,
                home_close_spread REAL,
                away_close_spread REAL,
                total_open REAL,
                total_close REAL,
                source_file TEXT,
                imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_date, home_team, away_team, bookmaker)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_historical_odds_lookup ON historical_odds(game_date, home_team, away_team)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_historical_odds_season ON historical_odds(season)"
        )

        # Table for the latest in-game snapshot per active/live game.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS live_game_state (
                game_id TEXT PRIMARY KEY,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                commence_time TEXT,
                home_score INTEGER DEFAULT 0,
                away_score INTEGER DEFAULT 0,
                quarter TEXT,
                time_remaining_str TEXT,
                seconds_remaining INTEGER,
                live_home_price REAL,
                live_home_point REAL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_live_game_last_updated ON live_game_state(last_updated)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_live_game_seconds_remaining ON live_game_state(seconds_remaining)"
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS referee_game_logs (
                game_id TEXT NOT NULL,
                official_id INTEGER NOT NULL,
                official_name TEXT NOT NULL,
                game_date TEXT,
                home_team TEXT,
                away_team TEXT,
                home_win INTEGER,
                total_points REAL,
                total_fouls REAL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (game_id, official_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ref_game_logs_official ON referee_game_logs(official_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ref_game_logs_date ON referee_game_logs(game_date)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS referee_stats (
                official_id INTEGER PRIMARY KEY,
                official_name TEXT NOT NULL,
                games_officiated INTEGER DEFAULT 0,
                home_win_pct REAL DEFAULT 0.5,
                avg_total_points REAL DEFAULT 0.0,
                avg_fouls_called REAL DEFAULT 0.0,
                over_index REAL DEFAULT 0.0,
                home_bias REAL DEFAULT 0.0,
                last_game_date TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_injuries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_abbr TEXT NOT NULL,
                status TEXT NOT NULL,
                vorp REAL DEFAULT 0.0
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_daily_injuries_date ON daily_injuries(date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_daily_injuries_team_date ON daily_injuries(team_abbr, date)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_injury_impact (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                team_abbr TEXT NOT NULL,
                total_vorp_missing REAL DEFAULT 0.0,
                injury_modifier REAL DEFAULT 0.0,
                UNIQUE(date, team_abbr)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_team_injury_impact_date ON team_injury_impact(date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_team_injury_impact_team_date ON team_injury_impact(team_abbr, date)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_injury_status (
                game_id TEXT NOT NULL,
                team_abbr TEXT NOT NULL,
                game_date TEXT,
                inactive_player_ids TEXT,
                inactive_player_names TEXT,
                expected_value REAL,
                active_value REAL,
                injury_impact REAL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (game_id, team_abbr)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_team_injury_date ON team_injury_status(game_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_team_injury_team_date ON team_injury_status(team_abbr, game_date)"
        )
        conn.commit()
    finally:
        conn.close()

if os.environ.get("MARKET_DB_INIT_ON_IMPORT", "1") == "1":
    # Legacy dev mode can still auto-bootstrap sqlite. Deployment should disable this
    # and rely on Flask-Migrate / Alembic instead.
    init_db()
