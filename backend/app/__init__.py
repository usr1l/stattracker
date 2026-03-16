"""Flask application factory."""
import os

from flask import Flask
from flask_cors import CORS

from app.api.players import bp as players_bp
from app.api.stats import bp as stats_bp
from app.api.analysis import bp as analysis_bp
from app.api.market import bp as market_bp
from app.api.predictions import bp as predictions_bp

def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
    app.register_blueprint(players_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(predictions_bp)

    if os.environ.get("ENABLE_SCHEDULER", "1") == "1":
        from scheduler import start_scheduler

        start_scheduler()

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
