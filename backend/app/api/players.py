"""Players API blueprint."""
from flask import Blueprint, jsonify, request

from app.services import players as players_service

bp = Blueprint("players", __name__, url_prefix="/api/players")


@bp.route("", methods=["GET"])
def list_players():
    """GET /api/players - List all NBA players."""
    try:
        players = players_service.get_all_players()
        return jsonify(players)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/search", methods=["GET"])
def search_players():
    """GET /api/players/search?q=lebron - Search players by name."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    try:
        players = players_service.search_players(q)
        return jsonify(players)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:player_id>", methods=["GET"])
def get_player(player_id):
    """GET /api/players/:id - Get a single player by ID."""
    player = players_service.get_player_by_id(player_id)
    if player is None:
        return jsonify({"error": "Player not found"}), 404
    return jsonify(player)


@bp.route("/teams", methods=["GET"])
def list_teams():
    """GET /api/players/teams - List all NBA teams."""
    try:
        teams = players_service.get_teams()
        return jsonify(teams)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/teams/<team_name>/roster", methods=["GET"])
def get_team_roster(team_name):
    """GET /api/players/teams/:team/roster - Get roster for a team."""
    roster = players_service.get_team_roster(team_name)
    if roster is None:
        return jsonify({"error": "Team not found"}), 404
    return jsonify(roster)
