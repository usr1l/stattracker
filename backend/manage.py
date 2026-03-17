"""Minimal Flask app entrypoint for CLI commands such as migrations."""
from bootstrap import configure_paths

configure_paths()

from app import create_app

app = create_app()
