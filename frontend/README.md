# StatTracker Frontend

Minimal Vite + React client for the daily NBA slate.

## Run

From the project root, or from `frontend/`:

```bash
npm run reset-dev
```

That starts:

- the Flask backend on `http://localhost:5001`
- the Vite frontend on `http://localhost:3000`

## Environment

- By default the frontend calls `/api/*` on the current origin and relies on the Vite dev proxy to reach `http://127.0.0.1:5001`
- Set `VITE_API_BASE_URL` only when you want the browser to call a non-default backend directly
