# StatTracker Flask Backend

## Run

From project root:

```bash
# Install dependencies (if not already)
pip install -r backend/requirements.txt
# Or use project venv
.venv/bin/pip install -r backend/requirements.txt

# Start server (from project root)
.venv/bin/python backend/run.py
```

Or from `backend/`:

```bash
cd backend
../.venv/bin/python run.py
```

Server runs at http://localhost:5000

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
