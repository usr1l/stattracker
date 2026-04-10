# StatTracker Flask Backend

## Python

Use Python 3.11 for the backend runtime.

## Run

From project root:

```bash
# Create a Python 3.11 virtualenv if you do not already have one
python3.11 -m venv .venv

# Install the reproducible backend dependency set
.venv/bin/pip install -r backend/requirements.lock.txt

# Start server (from project root)
.venv/bin/python backend/run.py
```

If you need to refresh dependency constraints, edit `backend/requirements.txt` and then
regenerate `backend/requirements.lock.txt` from a clean Python 3.11 environment.

Or from `backend/`:

```bash
cd backend
../.venv/bin/python run.py
```

For a lighter local smoke run without catch-up jobs or the scheduler:

```bash
cd backend
STARTUP_CATCHUP_MODE=skip START_LOCAL_SCHEDULER_ON_RUN=0 ../.venv/bin/python run.py
```

Server runs at http://localhost:5001 by default.

## Endpoints

- `GET /health` - Health check
- `GET /api/players` - List all players
- `GET /api/players/search?q=name` - Search players
- `GET /api/players/teams` - List teams
- `GET /api/players/teams/:team/roster` - Team roster
- `GET /api/stats/player/:id/career` - Career stats
- `GET /api/stats/player/:id/gamelogs` - Game logs (query params: matchup, num_games, pts, reb, ast, etc.)
- `POST /api/analysis/probability` - Stat line probability
- `POST /api/analysis/combination` - Same-game combo probability
- `POST /api/analysis/probability-table` - Probability table for combos

### Prediction & Market Endpoints (Phase 1)
- `GET /api/predictions/elo` - Current ELO ratings for all teams
- `GET /api/predictions/game?home=HOU&away=DAL&date=YYYY-MM-DD` - Pre-game prediction
- `GET /api/predictions/trends/:team` - Rolling stats trends for a team
- `POST /api/predictions/backtest` - Run historical backtest
- `GET /api/market/surges` - Recent market surges (sharp action)
- `GET /api/market/odds/:game_id` - Current odds & line movement
- `GET /api/market/futures` - Latest futures odds
- `GET /api/schedule/today` - Lightweight slate for the current Eastern date
