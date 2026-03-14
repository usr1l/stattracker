"""Analysis API blueprint."""
from flask import Blueprint, jsonify, request

from app.services import analysis as analysis_service

bp = Blueprint("analysis", __name__, url_prefix="/api/analysis")


@bp.route("/probability", methods=["POST"])
def cat_probability():
    """POST /api/analysis/probability - Single-player stat line probability.
    Body: { player_id?: number, logs?: [...], ast?, reb?, pts?, stl?, blk?, pf?, threes_made?, triple_double?, double_double?, win? }
    """
    data = request.get_json() or {}
    try:
        result = analysis_service.get_cat_probability(
            logs=data.get("logs"),
            player_id=data.get("player_id"),
            ast=data.get("ast"),
            reb=data.get("reb"),
            pts=data.get("pts"),
            stl=data.get("stl"),
            blk=data.get("blk"),
            pf=data.get("pf"),
            threes_made=data.get("threes_made"),
            triple_double=data.get("triple_double"),
            double_double=data.get("double_double"),
            win=data.get("win"),
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/combination", methods=["POST"])
def combination_probability():
    """POST /api/analysis/combination - Multi-player same-game combo probability.
    Body: { player_ids: [id1, id2], players: [{ast, reb, pts, stl, blk} or {total_pra} or {total_sb}], combine?: 'all'|'pra'|'sb' }
    """
    data = request.get_json() or {}
    player_ids = data.get("player_ids", [])
    players = data.get("players", [])
    combine = data.get("combine", "all")
    try:
        result = analysis_service.get_combination_probability(
            player_ids=player_ids,
            players=players,
            combine=combine,
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/probability-table", methods=["POST"])
def probability_table():
    """POST /api/analysis/probability-table - Probability table for multi-player combos.
    Body: { player_ids: [id1, id2], cats?: [...], graph_size?: 31 }
    """
    data = request.get_json() or {}
    player_ids = data.get("player_ids", [])
    cats = data.get("cats")
    graph_size = data.get("graph_size", 31)
    try:
        result = analysis_service.get_probability_table_combos(
            player_ids=player_ids,
            cats=cats,
            graph_size=graph_size,
        )
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/averages", methods=["POST"])
def cat_averages():
    """POST /api/analysis/averages - Get average stats for game logs.
    Body: { logs: [...], cats?: [...] }
    """
    data = request.get_json() or {}
    logs = data.get("logs", [])
    cats = data.get("cats")
    try:
        result = analysis_service.get_cat_averages(logs=logs, cats=cats)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
