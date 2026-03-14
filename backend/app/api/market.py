"""Market surveillance endpoints."""
from flask import Blueprint, jsonify, request
from market.db import get_db

bp = Blueprint("market", __name__, url_prefix="/api/market")

@bp.route("/surges", methods=["GET"])
def get_surges():
    """GET active market surges (line movement, volume, futures)."""
    conn = get_db()
    try:
        # Get signals from last 48 hours
        rows = conn.execute("""
            SELECT signal_type, game_id, team, description, magnitude, timestamp 
            FROM market_signals 
            WHERE timestamp >= datetime('now', '-2 days')
            ORDER BY timestamp DESC
        """).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()

@bp.route("/odds/<game_id>", methods=["GET"])
def get_game_odds(game_id):
    """GET current odds and full movement history for a game."""
    from market.line_movement import get_game_line_history
    try:
        history = get_game_line_history(game_id)
        if not history:
            return jsonify({"error": "No odds found for game"}), 404
        return jsonify({
            "current_line": history[-1],
            "history": history,
            "movement_total": history[-1]["home_point"] - history[0]["home_point"] if history[0]["home_point"] and history[-1]["home_point"] else 0
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/futures", methods=["GET"])
def get_futures():
    """GET latest futures odds (e.g. championship winner)."""
    conn = get_db()
    try:
        # Get latest price for each team
        rows = conn.execute("""
            SELECT market, team, price, timestamp 
            FROM futures_history f1
            WHERE timestamp = (
                SELECT MAX(timestamp) 
                FROM futures_history f2 
                WHERE f1.team = f2.team AND f1.market = f2.market
            )
            ORDER BY price ASC
        """).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()
