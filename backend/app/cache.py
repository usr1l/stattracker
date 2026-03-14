"""SQLite cache layer for NBA data."""
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional, Union

from app.config import CACHE_PATH


def _get_conn() -> sqlite3.Connection:
    """Get a connection to the cache database."""
    conn = sqlite3.connect(str(CACHE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    """Create cache table if it doesn't exist."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _make_key(prefix: str, *parts: Any) -> str:
    """Build a cache key from prefix and parts (JSON-serializable)."""
    payload = json.dumps(parts, sort_keys=True, default=str)
    h = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"{prefix}_{h}"


def get_cached(key: str) -> Optional[Any]:
    """Retrieve a value from cache. Returns None if missing or expired."""
    _init_db()
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] < time.time():
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            return None
        return json.loads(row["value"])
    finally:
        conn.close()


def set_cached(key: str, value: Any, ttl_hours: float) -> None:
    """Store a value in cache with TTL in hours."""
    _init_db()
    conn = _get_conn()
    try:
        expires_at = time.time() + (ttl_hours * 3600)
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value, default=str), expires_at),
        )
        conn.commit()
    finally:
        conn.close()


def make_gamelogs_key(player_id: Union[str, int], **filters: Any) -> str:
    """Build cache key for player game logs."""
    return _make_key("gamelogs", str(player_id), filters)
