"""Prediction endpoints."""
from flask import Blueprint, jsonify, request

from prediction.elo import load_elo
from prediction.trends import get_team_trends
from prediction.predict import predict_game

bp = Blueprint("predictions", __name__, url_prefix="/api/predictions")

@bp.route("/elo", methods=["GET"])
def get_elo_ratings():
    """GET current ELO rankings for all teams."""
    try:
        ratings = load_elo()
        # Sort descending
        sorted_ratings = dict(sorted(ratings.items(), key=lambda item: item[1], reverse=True))
        return jsonify(sorted_ratings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/game", methods=["GET"])
def get_game_prediction():
    """GET /api/predictions/game?home=BOS&away=LAL&date=2025-10-25"""
    home = request.args.get("home")
    away = request.args.get("away")
    date_str = request.args.get("date")
    game_id = request.args.get("game_id")
    
    if not all([home, away, date_str]):
        return jsonify({"error": "Missing home, away, or date params"}), 400
        
    try:
        pred = predict_game(home, away, date_str, game_id)
        return jsonify(pred)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/trends/<team>", methods=["GET"])
def get_trends(team):
    """GET rolling trends and momentum score for a team."""
    try:
        trends = get_team_trends(team)
        return jsonify(trends)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/backtest", methods=["POST"])
def run_backtest_route():
    """POST run a backtest on historical data."""
    data = request.get_json() or {}
    games = data.get("games", [])
    bankroll = data.get("starting_bankroll", 10000.0)
    
    if not games:
        return jsonify({"error": "No games provided for backtest"}), 400
        
    from prediction.backtest import run_backtest
    try:
        results = run_backtest(games, bankroll)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
