# StatTracker Frontend

React app (Vite). Connects to Flask backend via dev proxy.

## Run

1. Start the backend (from project root):
   ```bash
   .venv/bin/python backend/run.py
   ```

2. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open http://localhost:5173

The frontend proxies `/api` and `/health` to the backend at http://localhost:5000.
