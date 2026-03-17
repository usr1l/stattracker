"""Shared runtime bootstrap for web and worker entrypoints."""
import os
import sys
from pathlib import Path


def configure_paths() -> tuple[Path, Path]:
    """Ensure backend and project-root paths resolve consistently."""
    backend_dir = Path(__file__).resolve().parent
    project_root = backend_dir.parent

    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    if str(project_root) not in sys.path:
        sys.path.insert(1, str(project_root))

    os.chdir(str(project_root))
    return backend_dir, project_root


def prepare_runtime(fetch_players: bool = True) -> Path:
    """Bootstrap seasons, players, and cached prediction assets."""
    _, project_root = configure_paths()

    from app.logger import configure_logging, get_logger

    configure_logging()
    logger = get_logger(__name__)

    from season import load_seasons, refresh_seasons

    current_season, _ = refresh_seasons()
    os.environ["CURRENT_SEASON"] = current_season

    if fetch_players:
        from get_players import get_nba_players_csv

        players_csv_path = project_root / "players_csv" / "nba_players.csv"
        players_csv_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            get_nba_players_csv()
        except Exception as exc:
            logger.warning("Player CSV refresh failed during bootstrap: %s", exc)

    from prediction.elo import ELO_FILE
    from prediction.elo_builder import build_elo_from_history
    from prediction.team_stats import has_team_game_logs, refresh_team_stats

    if not has_team_game_logs():
        _, seasons = load_seasons()
        try:
            refresh_team_stats(seasons)
        except Exception as exc:
            logger.warning("Team stats bootstrap failed: %s", exc)

    if not ELO_FILE.exists():
        _, seasons = load_seasons()
        try:
            build_elo_from_history(seasons)
        except Exception as exc:
            logger.warning("ELO bootstrap failed: %s", exc)

    return project_root
