"""Entry point for the Flask backend."""
import os
import sys
from pathlib import Path

# Backend dir first so "app" resolves to backend/app, not project root app.py
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(os.path.dirname(backend_dir))
sys.path.insert(0, backend_dir)
sys.path.insert(1, project_root)
os.chdir(str(project_root))  # So get_nba_players_csv writes to players_csv/ at project root

# Refresh seasons and fetch players before loading app (so config gets fresh data)
from season import refresh_seasons

current_season, _ = refresh_seasons()
os.environ["CURRENT_SEASON"] = current_season

from get_players import get_nba_players_csv

get_players_csv_path = project_root / "players_csv" / "nba_players.csv"
get_players_csv_path.parent.mkdir(parents=True, exist_ok=True)
get_nba_players_csv()

from prediction.elo import ELO_FILE
from prediction.elo_builder import build_elo_from_history
from prediction.team_stats import has_team_game_logs, refresh_team_stats
from season import load_seasons

# Bootstrap team logs only if cache table is empty.
if not has_team_game_logs():
    _, seasons = load_seasons()
    try:
        refresh_team_stats(seasons)
    except Exception as exc:
        print(f"Warning: team stats bootstrap failed: {exc}")

# Bootstrap ELO file only when missing.
if not ELO_FILE.exists():
    _, seasons = load_seasons()
    try:
        build_elo_from_history(seasons)
    except Exception as exc:
        print(f"Warning: ELO bootstrap failed: {exc}")

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
