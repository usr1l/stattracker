"""Prediction endpoints."""
import math
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from flask import Blueprint, jsonify, request
from nba_api.stats.static import teams as nba_teams

from market.db import get_db
from prediction.elo import load_elo
from prediction.props import project_player_stat
from prediction.trends import get_team_trends
from prediction.predict import predict_game
from app.services.analysis import get_cat_probability
from app.services.statistics import get_player_game_logs

bp = Blueprint("predictions", __name__, url_prefix="/api/predictions")
EASTERN = ZoneInfo("America/New_York")
TEAM_BY_ID = {int(team["id"]): team for team in nba_teams.get_teams()}


def _decimal_odds_to_prob(price):
    try:
        price = float(price)
    except (TypeError, ValueError):
        return None
    if price <= 1.0:
        return None
    return 1.0 / price


def _latest_market_snapshot(game_id):
    """Get the latest h2h/spread/total rows for a game from odds_history."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT market_type, home_price, away_price, home_point, away_point
            FROM odds_history
            WHERE game_id = ?
            ORDER BY timestamp DESC
            """,
            (game_id,),
        ).fetchall()
    finally:
        conn.close()

    latest = {}
    for row in rows:
        market_type = row["market_type"]
        if market_type not in latest:
            latest[market_type] = dict(row)
    return latest


def _load_scoreboard_games(date_str):
    """Fetch scoreboard rows for a date and map them into a lightweight schedule payload."""
    from nba_api.stats.endpoints import ScoreboardV2

    target = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m/%d/%Y")
    try:
        df = ScoreboardV2(game_date=target).get_data_frames()[0]
    except TypeError:
        df = ScoreboardV2(game_date=target, day_offset=0).get_data_frames()[0]

    games = []
    for _, row in df.iterrows():
        home_team = TEAM_BY_ID.get(int(row["HOME_TEAM_ID"]), {})
        away_team = TEAM_BY_ID.get(int(row["VISITOR_TEAM_ID"]), {})
        home_abbr = str(home_team.get("abbreviation") or "")
        away_abbr = str(away_team.get("abbreviation") or "")
        if not home_abbr or not away_abbr:
            continue

        games.append(
            {
                "game_id": str(row["GAME_ID"]),
                "status": str(row.get("GAME_STATUS_TEXT") or ""),
                "home_team": home_abbr,
                "away_team": away_abbr,
                "home_name": str(home_team.get("full_name") or home_abbr),
                "away_name": str(away_team.get("full_name") or away_abbr),
            }
        )
    return games

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
    """GET a consolidated game prediction with direct model projections."""
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


@bp.route("/dashboard", methods=["GET"])
def get_dashboard_predictions():
    """GET a scoreboard-backed list of today's games with model and market context."""
    date_str = request.args.get("date") or datetime.now(EASTERN).date().isoformat()

    try:
        games = _load_scoreboard_games(date_str)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    payload = []
    for game in games:
        try:
            prediction = predict_game(
                game["home_team"],
                game["away_team"],
                date_str,
                game["game_id"],
            )
            model_projection = prediction.get("projections", {})
            market = _latest_market_snapshot(game["game_id"])
            h2h = market.get("h2h", {})
            spreads = market.get("spreads", {})
            totals = market.get("totals", {})
            home_implied_prob = _decimal_odds_to_prob(h2h.get("home_price"))
            home_model_prob = model_projection.get("home_win_prob")
            edge = None
            if home_model_prob is not None and home_implied_prob is not None:
                edge = float(home_model_prob) - float(home_implied_prob)

            payload.append(
                {
                    "game_id": game["game_id"],
                    "date": date_str,
                    "status": game["status"],
                    "home_team": game["home_team"],
                    "away_team": game["away_team"],
                    "home_name": game["home_name"],
                    "away_name": game["away_name"],
                    "model": {
                        "home_win_prob": model_projection.get("home_win_prob"),
                        "projected_spread": model_projection.get("projected_spread"),
                        "projected_total": model_projection.get("projected_total"),
                        "top_features": model_projection.get("top_features", [])[:3],
                        "model_source": model_projection.get("model_source", {}),
                    },
                    "market": {
                        "home_price": h2h.get("home_price"),
                        "away_price": h2h.get("away_price"),
                        "spread": spreads.get("home_point"),
                        "total": totals.get("home_point"),
                        "implied_home_prob": home_implied_prob,
                    },
                    "edge": edge,
                    "trend_flags": prediction.get("trends", {}),
                    "market_signals": prediction.get("market_signals", []),
                }
            )
        except Exception as exc:
            payload.append(
                {
                    "game_id": game["game_id"],
                    "date": date_str,
                    "status": game["status"],
                    "home_team": game["home_team"],
                    "away_team": game["away_team"],
                    "home_name": game["home_name"],
                    "away_name": game["away_name"],
                    "error": str(exc),
                }
            )

    payload.sort(key=lambda item: abs(float(item["edge"])) if item.get("edge") is not None else -1.0, reverse=True)
    return jsonify(payload)

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
    kelly_fraction = data.get("kelly_fraction", 0.25)
    seasons = data.get("seasons")
    date_from = data.get("date_from")
    date_to = data.get("date_to")
    limit = data.get("limit")

    if isinstance(seasons, str):
        seasons = [item.strip() for item in seasons.split(",") if item.strip()]

    from prediction.backtest import run_backtest
    try:
        results = run_backtest(
            games or None,
            bankroll,
            kelly_fraction=kelly_fraction,
            seasons=seasons,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/train", methods=["POST"])
def train_models_route():
    """POST train consolidated prediction models from historical data."""
    data = request.get_json(silent=True) or {}
    seasons = data.get("seasons")

    from prediction.train import train_from_history

    try:
        result = train_from_history(seasons=seasons)
        status = 200 if result.get("ok") else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/player-props", methods=["GET"])
def get_player_props_prediction():
    """GET player prop hit probability from historical game logs."""
    player_id = request.args.get("player_id")
    stat = (request.args.get("stat") or "PTS").upper()
    line_raw = request.args.get("line")
    num_games = request.args.get("num_games", default=50, type=int)

    if not player_id or line_raw is None:
        return jsonify({"error": "Missing player_id or line param"}), 400

    try:
        line = float(line_raw)
    except ValueError:
        return jsonify({"error": "line must be numeric"}), 400

    stat_map = {
        "PTS": "pts",
        "REB": "reb",
        "AST": "ast",
        "STL": "stl",
        "BLK": "blk",
        "FG3M": "threes_made",
    }
    if stat not in stat_map:
        return jsonify({"error": f"Unsupported stat '{stat}'"}), 400

    prop_threshold = int(math.floor(line) + 1)
    kwargs = {stat_map[stat]: prop_threshold}
    probability = get_cat_probability(player_id=player_id, **kwargs)
    if "error" in probability:
        return jsonify(probability), 400

    logs = get_player_game_logs(player_id, num_games=num_games)
    if not logs:
        return jsonify({"error": "No game logs found"}), 404

    df = pd.DataFrame(logs)
    if stat not in df.columns:
        return jsonify({"error": f"Stat column '{stat}' missing in game logs"}), 400

    l10_avg = float(df.head(10)[stat].mean()) if len(df) >= 1 else 0.0
    over_pct = float(probability["hit"]) / float(probability["total"]) if probability["total"] else 0.0

    return jsonify(
        {
            "player_id": int(player_id),
            "stat": stat,
            "line": line,
            "line_threshold_integer": prop_threshold,
            "over_pct": over_pct,
            "sample_size": int(probability["total"]),
            "l10_avg": l10_avg,
            "implied_prob_vs_line": over_pct,
            "criteria": probability["criteria"],
        }
    )


@bp.route("/props/advanced", methods=["GET"])
def get_advanced_player_props_prediction():
    """GET a model-based player prop projection with matchup modifiers and edge."""
    player_id = request.args.get("player_id", type=int)
    stat = (request.args.get("stat") or "").upper()
    line_raw = request.args.get("line")
    opponent = request.args.get("opponent")
    game_date = request.args.get("date")

    if player_id is None or not stat or line_raw is None or not opponent:
        return jsonify({"error": "Missing player_id, stat, line, or opponent param"}), 400

    try:
        sportsbook_line = float(line_raw)
    except ValueError:
        return jsonify({"error": "line must be numeric"}), 400

    try:
        projection = project_player_stat(
            player_id=player_id,
            stat=stat,
            opponent_team=opponent,
            game_date=game_date,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    projected_line = float(projection["projected_line"])
    edge_value = projected_line - sportsbook_line
    if edge_value > 0:
        recommended_bet = "OVER"
    elif edge_value < 0:
        recommended_bet = "UNDER"
    else:
        recommended_bet = "PASS"

    return jsonify(
        {
            "player_id": int(player_id),
            "stat": projection["stat"],
            "sportsbook_line": sportsbook_line,
            "projected_line": round(projected_line, 2),
            "modifiers_applied": {
                "base_projection": round(projection["modifiers_applied"]["base_projection"], 3),
                "opponent_defense_mod": round(projection["modifiers_applied"]["opponent_defense_mod"], 3),
                "pace_mod": round(projection["modifiers_applied"]["pace_mod"], 3),
            },
            "edge_value": round(edge_value, 2),
            "recommended_bet": recommended_bet,
        }
    )
