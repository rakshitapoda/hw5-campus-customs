# Campus Customs Multi-Agent Operations

An agentic system that runs the Campus Customs shop. Open tickets (customer orders, rent notices, discount requests) are worked by a team of five PydanticAI agents. The agents use an MCP server to read and update the shop database, and a human watches and approves payments from a React dashboard.

```
React dashboard (frontend/, :5173)
        │  HTTP
FastAPI backend (backend/main.py, :8000)
        │  runs the agent team: Boss · Inventory · Accounting · Facilities · Customer Service
        │  (every agent uses gpt-6-luna through Portkey)
MCP server (mcp_server/server.py, stdio)
        │
data/campus_customs_new.db   ← working copy; data/campus_customs.db is the untouched original
```

**Shop rules the system enforces:**
- Today is `desk.date_today`.
- Lead times come from `vendors`.
- Vendors with an open invoice won't ship.
- Every payment needs human approval.
- Cash can never go negative, and cash only flows out.
- Customer and vendor messages are drafts only.

## Project layout

| Path | What it is |
|---|---|
| `data/campus_customs.db` | Original database (never modified) |
| `data/campus_customs_new.db` | Working copy the MCP server reads and writes |
| `mcp_server/server.py` | FastMCP server with 15 tools (see `mcp_server/README.md`) |
| `.mcp.json` | MCP connection config for Claude Code (`campus-customs`) |
| `backend/main.py` | FastAPI routes for the dashboard |
| `backend/models.py` | Pydantic data types |
| `backend/prompts/*.md` | One prompt per agent |
| `backend/agents/`, `backend/team.py`, `backend/audit.py`, `backend/run_tickets.py` | Agent definitions, shared agent setup (model, MCP toolset, delegation, guardrails), audit logging, CLI runner |
| `frontend/` | React + Vite + TypeScript Operations Desk |
| `output/` | Harness, smoke tests, audit trail, ticket plan/results, dashboard screenshots, design notes |
| `AI_prompts.md` | Log of every prompt used to build the project |

## Setup (one time)

Requires Python 3.13 and Node 20+.

```bash
# from the hw5/ folder
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt

cd frontend && npm install && cd ..

cp .env.example .env        # then put your real PORTKEY_API_KEY in .env
```

You can also `export PORTKEY_API_KEY=...` in your shell instead of using `.env`. The real `.env` is git-ignored. Never commit it.

## 1. Reset the database

Every complete ticket-resolution run starts from a fresh copy of the original database. Use any of these:

```bash
# a) copy the original over the working copy (works without any server running)
cp data/campus_customs.db data/campus_customs_new.db

# b) through the backend (also clears approvals/decisions on the dashboard board)
curl -X POST http://localhost:8000/api/reset
```

You can also click **Reset desk** in the dashboard's top bar, which does the same as (b). The CLI full run (`.venv/bin/python -m backend.run_tickets`) resets automatically before it starts.

## 2. Start the MCP server

The backend starts the MCP server for you, so for normal use you can skip this step. To run it on its own (stdio transport):

```bash
.venv/bin/python mcp_server/server.py
```

**In Claude Code:** open this folder and approve the `campus-customs` server from `.mcp.json` when prompted. `/mcp` shows whether it's connected.

## 3. Start the FastAPI backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs. Main routes:

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/tickets` | All tickets, open/resolved status, latest agent result |
| POST | `/api/tickets/{id}/run` | Run the agent team on a ticket (in the background) |
| GET | `/api/runs/{run_id}` | Status of a run |
| POST | `/api/tickets/{id}/decision` | Record a human decision (e.g. discount level) |
| GET | `/api/activity` | Recent agent activity (what each agent said, which tools it used) |
| GET | `/api/approvals` | Payments/purchases the agents prepared |
| POST | `/api/approvals/{id}/approve` | Human approval. The only route that moves money |
| GET | `/api/cash` | Checking balance |
| POST | `/api/reset` | Reset the working database |

## 4. Start the React dashboard

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. Then:

1. Pick a ticket and click **Start agent team**. You'll see each agent's status, what it says, and which tools it calls.
2. Type your name in **Approving as**, then approve payments in the **Sign-off tray**. The checking balance updates after each approval.
3. For tickets marked **Needs a decision**, record your call in **Your decision**, then run the agents again.

The backend URL defaults to `http://localhost:8000`. Override it with `VITE_API_URL` (see `frontend/.env.example`).

## Results

The full run resolved all three tickets. Checking went from $3,400.00 to $152.00, through three human-approved payments: invoice #501 ($840), the tee restock ($8), and rent ($2,400). See `output/desk_tickets.html` (expected vs. actual, Cash, Reflection), `output/resolved_tickets.json`, and `output/resolved_board.html`. The full system description is in `output/harness.md`.
