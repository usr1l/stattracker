"""Stats API blueprint."""
from typing import List, Optional

from flask import Blueprint, jsonify, request

from app.services import statistics as stats_service

bp = Blueprint("stats", __name__, url_prefix="/api/stats")


def _parse_bool(val: Optional[str]) -> Optional[bool]:
    if val is None:
        return None
    return str(val).lower() in ("true", "1", "yes")


def _parse_int(val: Optional[str]) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _parse_seasons(val: Optional[str]) -> Optional[List[str]]:
    if val is None or val == "":
        return None
    try:
        import ast
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return None


@bp.route("/player/<int:player_id>/career", methods=["GET"])
def get_career_stats(player_id):
    """GET /api/stats/player/:id/career - Get career stats."""
    try:
        stats = stats_service.get_player_career_stats(player_id)
        if stats is None:
            return jsonify({"error": "Player not found or no career data"}), 404
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/player/<int:player_id>/gamelogs", methods=["GET"])
def get_game_logs(player_id):
    """GET /api/stats/player/:id/gamelogs - Get filtered game logs.
    Query params: matchup, seasons, num_games, home, away, ast, reb, pts, stl, blk, pf, threes_made, triple_double, double_double, win
    """
    try:
        seasons = _parse_seasons(request.args.get("seasons"))
        logs = stats_service.get_player_game_logs(
            player_id=player_id,
            matchup=request.args.get("matchup", ""),
            seasons=seasons,
            num_games=_parse_int(request.args.get("num_games")) or 20,
            home=_parse_bool(request.args.get("home")) or False,
            away=_parse_bool(request.args.get("away")) or False,
            ast=_parse_int(request.args.get("ast")),
            reb=_parse_int(request.args.get("reb")),
            pts=_parse_int(request.args.get("pts")),
            stl=_parse_int(request.args.get("stl")),
            blk=_parse_int(request.args.get("blk")),
            pf=_parse_int(request.args.get("pf")),
            threes_made=_parse_int(request.args.get("threes_made")),
            triple_double=_parse_bool(request.args.get("triple_double")),
            double_double=_parse_bool(request.args.get("double_double")),
            win=_parse_bool(request.args.get("win")),
        )
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
