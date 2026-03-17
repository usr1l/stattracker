"""Live in-game betting endpoints."""
from flask import Blueprint, jsonify

from live.engine import list_live_games

bp = Blueprint("live", __name__, url_prefix="/api/live")


@bp.route("/games", methods=["GET"])
def get_live_games():
    """GET current live-game probabilities and live market edges."""
    try:
        return jsonify(list_live_games())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
