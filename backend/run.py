"""Entry point for the Flask backend."""
import os
import sys

# Backend dir first so "app" resolves to backend/app, not project root app.py
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(1, project_root)
os.chdir(project_root)  # So get_nba_players_csv writes to players_csv/ at project root

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
