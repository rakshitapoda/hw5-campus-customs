# Campus Customs — Operations Desk (frontend)

React + Vite + TypeScript dashboard for the Campus Customs agent team.

```bash
# 1. backend (from the project root)
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000

# 2. frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
```

The API URL defaults to `http://localhost:8000`. Override it with `VITE_API_URL` (see `.env.example`).

- `src/api.ts`: typed client for the FastAPI routes
- `src/agents.ts`: agent colors/roles and the logic that turns audit events into live agent status
- `src/components/`: ticket queue, agent floor, live feed, agent summaries, cash card, sign-off tray

Design notes: `../output/design.md`.
