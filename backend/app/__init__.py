"""Flask application factory."""
from pathlib import Path

from flask import Flask
from flask_cors import CORS

from app.config import CORS_ORIGINS, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from app.extensions import db, migrate
from app.api.players import bp as players_bp
from app.api.stats import bp as stats_bp
from app.api.analysis import bp as analysis_bp
from app.api.live import bp as live_bp
from app.api.market import bp as market_bp
from app.api.predictions import bp as predictions_bp
from app.api.schedule import bp as schedule_bp
from app.logger import configure_logging

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    if SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "connect_args": {
                "check_same_thread": False,
                "timeout": 30,
            }
        }

    configure_logging(app)
    db.init_app(app)
    migrate.init_app(app, db, directory=str(MIGRATIONS_DIR))

    # Import models so Flask-Migrate discovers the metadata.
    from app import models  # noqa: F401

    CORS(app, origins=CORS_ORIGINS, supports_credentials=True)
    app.register_blueprint(players_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(live_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(schedule_bp)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
