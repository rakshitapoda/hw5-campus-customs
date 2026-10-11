"""FastAPI backend for the Campus Customs dashboard.

Run from the backend/ folder:

    uvicorn main:app --reload --port 8000

All shop data is read and written through the campus-customs MCP server
(data/campus_customs_new.db). Agents only *prepare* payments; the approve route
below is the only place money moves, and only with a named human approver.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:  # allow `uvicorn main:app` from inside backend/
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic_ai import ModelRetry  # noqa: E402

import backend.agents  # noqa: E402,F401  (registers all five agents)
from backend.audit import append_event, load_events  # noqa: E402
from backend.models import Approval, ApproveRequest, DecisionRequest, RunStatus, TeamDeps, TicketBudget  # noqa: E402
from backend.run_tickets import TICKET_TIMEOUT_SECONDS, reset_working_db  # noqa: E402
from backend.team import MCP_TOOLSET, MODEL_NAME, proposal_key, run_agent  # noqa: E402

BOARD_STATE_PATH = ROOT_DIR / "output" / "board_state.json"
CASH_ACCOUNT = "checking"
MAX_ACTIVITY_EVENTS = 500
ACTIVITY_EVENTS = {
    "run_start", "run_end", "agent_start", "model_response", "delegation", "delegation_refused",
    "agent_end", "agent_error", "ticket_timeout", "db_reset", "payment_approved", "approval_refused",
    "human_decision",
}
PROPOSAL_STATUS = {"awaiting_human_approval": "pending", "blocked": "blocked", "refused": "refused"}

RUN_LOCK = asyncio.Lock()       # one agent run at a time (they share one database)
STATE_LOCK = asyncio.Lock()     # serializes board_state.json updates and approvals
RUNS: dict[str, RunStatus] = {}
RUN_TASKS: set[asyncio.Task] = set()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------ board state
# output/board_state.json keeps what the board needs between requests:
# approvals (prepared payments / POs), each ticket's latest agent result
# (decision, message drafts), and human decisions on judgment calls.
# It is cleared by /api/reset.

EMPTY_STATE = {"approvals": [], "results": {}, "decisions": {}}


def load_state() -> dict:
    state = json.loads(BOARD_STATE_PATH.read_text()) if BOARD_STATE_PATH.exists() else {}
    return {**json.loads(json.dumps(EMPTY_STATE)), **state}


def save_state(state: dict) -> None:
    BOARD_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = BOARD_STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    os.replace(tmp, BOARD_STATE_PATH)


def approval_key(proposal: dict) -> tuple:
    # Rent is keyed by due date too, so next month's rent is a new item, not a repeat.
    return (*proposal_key(proposal), proposal.get("due_date") if proposal.get("kind") == "rent" else None)


def merge_proposals(state: dict, proposals: list[dict], run_id: str) -> None:
    """Turn prepare_* results from a run into approval items, without duplicating existing ones."""
    for proposal in proposals:
        status = PROPOSAL_STATUS.get(proposal.get("status"))
        if status is None:
            continue
        existing = next(
            (a for a in state["approvals"] if approval_key(a["proposal"]) == approval_key(proposal)), None
        )
        if existing and existing["status"] == "approved":
            continue  # already paid; never re-open it
        if existing:
            existing.update(status=status, proposal=proposal)
            continue
        state["approvals"].append(Approval(
            id=uuid.uuid4().hex[:8],
            item_type="payment" if "kind" in proposal else "purchase_order",
            ticket_id=proposal.get("prepared_for_ticket"),
            run_id=run_id,
            prepared_by=proposal.get("prepared_by"),
            status=status,
            proposal=proposal,
            created_at=now(),
        ).model_dump())


async def mcp(tool: str, args: dict | None = None):
    try:
        return await MCP_TOOLSET.direct_call_tool(tool, args or {})
    except ModelRetry as exc:  # ToolError from the MCP server
        raise HTTPException(status_code=409 if tool.startswith("execute_") else 404, detail=str(exc)) from exc


async def maybe_resolve(state: dict, ticket_id: int | None) -> bool:
    """Mark a ticket resolved once the agents said it only needed approvals and every one is approved."""
    if ticket_id is None:
        return False
    result = state["results"].get(str(ticket_id))
    items = [a for a in state["approvals"] if a["ticket_id"] == ticket_id]
    if not result or result["recommended_status"] != "awaiting_approval" or not items:
        return False
    if all(a["status"] == "approved" for a in items):
        await mcp("update_ticket_status", {"ticket_id": ticket_id, "status": "resolved"})
        return True
    return False


# -------------------------------------------------------------- agent runs

async def run_ticket(run: RunStatus) -> None:
    async with RUN_LOCK:
        async with STATE_LOCK:
            state = load_state()
        # Seed with items already awaiting approval so agents don't re-prepare them
        # and the cash check counts them in pending_total.
        seeded = [a["proposal"] for a in state["approvals"] if a["status"] == "pending"]
        deps = TeamDeps(run_id=run.run_id, ticket_id=run.ticket_id, agent="boss", chain=("boss",),
                        budget=TicketBudget(proposals=list(seeded)))
        prompt = f"Handle ticket {run.ticket_id}."
        decisions = state["decisions"].get(str(run.ticket_id), [])
        if decisions:
            prompt += "\n\nHuman decisions recorded on the board for this ticket (authoritative for these judgment calls):\n" + \
                "\n".join(f"- {d['decided_by']}: {d['decision']}" for d in decisions)
        append_event("run_start", run_id=run.run_id, model=MODEL_NAME, source="api", full_run=False,
                     requested_tickets=[run.ticket_id], human_decisions=decisions)
        try:
            resolution = await asyncio.wait_for(
                run_agent("boss", prompt, deps), timeout=TICKET_TIMEOUT_SECONDS
            )
        except TimeoutError:
            append_event("ticket_timeout", run_id=run.run_id, ticket_id=run.ticket_id, limit_seconds=TICKET_TIMEOUT_SECONDS)
            run.status, run.error, run.finished_at = "failed", f"Timed out after {TICKET_TIMEOUT_SECONDS}s", now()
            return
        except Exception as exc:  # already written to the audit trail by run_agent
            run.status, run.error, run.finished_at = "failed", f"{type(exc).__name__}: {exc}", now()
            return

        async with STATE_LOCK:
            state = load_state()
            merge_proposals(state, deps.budget.proposals, run.run_id)
            state["results"][str(run.ticket_id)] = {**resolution.model_dump(), "run_id": run.run_id, "finished_at": now()}
            if resolution.recommended_status == "resolved":
                await mcp("update_ticket_status", {"ticket_id": run.ticket_id, "status": "resolved"})
            save_state(state)
        append_event("run_end", run_id=run.run_id, ticket_ids=[run.ticket_id],
                     recommended_status=resolution.recommended_status)
        run.status, run.resolution, run.finished_at = "completed", resolution, now()


# ------------------------------------------------------------------- app

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with MCP_TOOLSET:  # one MCP server process for the app's lifetime
        yield


app = FastAPI(title="Campus Customs Backend", lifespan=lifespan)
# The Vite dev server (http://localhost:5173, or the next free port) may call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/tickets")
async def list_tickets():
    """All tickets with their open/resolved status and the latest agent result."""
    tickets = await mcp("list_tickets")
    async with STATE_LOCK:
        state = load_state()
    running = {r.ticket_id: r.run_id for r in RUNS.values() if r.status == "running"}
    out = []
    for t in tickets:
        result = state["results"].get(str(t["id"]))
        items = [a for a in state["approvals"] if a["ticket_id"] == t["id"]]
        out.append({
            **t,
            "running_run_id": running.get(t["id"]),
            "agent_result": result,
            "approvals": {s: sum(a["status"] == s for a in items) for s in ("pending", "blocked", "refused", "approved")},
            "decisions": state["decisions"].get(str(t["id"]), []),
        })
    return out


@app.post("/api/tickets/{ticket_id}/run", status_code=202, response_model=RunStatus)
async def run_ticket_route(ticket_id: int):
    """Start the agent team (Boss first) on one ticket. Runs in the background; poll /api/runs/{run_id}."""
    ticket = await mcp("get_ticket", {"ticket_id": ticket_id})
    if ticket["status"] == "resolved":
        raise HTTPException(409, f"Ticket {ticket_id} is already resolved.")
    if RUN_LOCK.locked():
        raise HTTPException(409, "Another agent run is in progress; try again when it finishes.")
    run = RunStatus(run_id=uuid.uuid4().hex[:12], ticket_id=ticket_id, status="running", started_at=now())
    RUNS[run.run_id] = run
    task = asyncio.create_task(run_ticket(run))
    RUN_TASKS.add(task)
    task.add_done_callback(RUN_TASKS.discard)
    return run


@app.post("/api/tickets/{ticket_id}/decision")
async def record_decision(ticket_id: int, body: DecisionRequest):
    """Record a human decision on a judgment call (e.g. discount level). It is passed to the agents on the next run.

    This never moves money: payments still need /api/approvals/{id}/approve.
    """
    ticket = await mcp("get_ticket", {"ticket_id": ticket_id})
    if ticket["status"] == "resolved":
        raise HTTPException(409, f"Ticket {ticket_id} is already resolved.")
    entry = {"decided_by": body.decided_by.strip(), "decision": body.decision.strip(), "decided_at": now()}
    async with STATE_LOCK:
        state = load_state()
        state["decisions"].setdefault(str(ticket_id), []).append(entry)
        save_state(state)
    append_event("human_decision", ticket_id=ticket_id, decided_by=entry["decided_by"], decision=entry["decision"])
    return {"ticket_id": ticket_id, **entry}


@app.get("/api/runs/{run_id}", response_model=RunStatus)
async def get_run(run_id: str):
    """Status of an agent run started by this server: running, completed (with the Boss's resolution), or failed."""
    if run_id not in RUNS:
        raise HTTPException(404, f"Run {run_id} not found.")
    return RUNS[run_id]


@app.get("/api/activity")
async def activity(limit: int = Query(50, ge=1, le=MAX_ACTIVITY_EVENTS), ticket_id: int | None = None,
                   run_id: str | None = None):
    """Recent agent activity from output/audit_trail.json, newest first: what each agent said and which tools it called."""
    events = [e for e in load_events() if e["event"] in ACTIVITY_EVENTS]
    if ticket_id is not None:
        events = [e for e in events if e.get("ticket_id") == ticket_id
                  or ticket_id in (e.get("requested_tickets") or e.get("ticket_ids") or [])]
    if run_id is not None:
        events = [e for e in events if e.get("run_id") == run_id]
    out = []
    for e in reversed(events[-limit:]):
        output = e.get("output") or {}
        out.append({
            "timestamp": e["timestamp"],
            "event": e["event"],
            "run_id": e.get("run_id"),
            "ticket_id": e.get("ticket_id"),
            "agent": e.get("agent"),
            "depth": e.get("depth"),
            "said": e.get("text") or output.get("decision") or output.get("summary") or e.get("task")
                    or e.get("reason") or e.get("error")
                    or (f"Approved by {e['approved_by']}" if e.get("approved_by") else None)
                    or (f"{e['decided_by']} decided: {e['decision']}" if e.get("decided_by") else None),
            "tools": [{"tool": c["tool"], "args": c["args"]} for c in e.get("tool_calls", []) if c["tool"] != "final_result"],
            "to_agent": e.get("to_agent"),
            "details": {k: e[k] for k in ("output", "approval", "execution", "prompt") if k in e} or None,
        })
    return out


@app.get("/api/approvals", response_model=list[Approval])
async def list_approvals(status: str | None = None, ticket_id: int | None = None):
    """Payments and purchase orders the agents prepared. Only 'pending' items can be approved."""
    async with STATE_LOCK:
        items = load_state()["approvals"]
    if status:
        items = [a for a in items if a["status"] == status]
    if ticket_id is not None:
        items = [a for a in items if a["ticket_id"] == ticket_id]
    return items


@app.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: str, body: ApproveRequest):
    """A human approves a prepared payment or purchase order. This is the only route that moves money.

    The MCP execute tool re-checks everything live (cash may not go negative,
    invoice must still be open, vendor must not be blocked), records the payment
    with approved_by, updates the invoice / lease, and debits cash.
    """
    async with STATE_LOCK:
        state = load_state()
        item = next((a for a in state["approvals"] if a["id"] == approval_id), None)
        if item is None:
            raise HTTPException(404, f"Approval {approval_id} not found.")
        if item["status"] != "pending":
            raise HTTPException(409, f"Approval {approval_id} is '{item['status']}' and cannot be approved.")

        p = item["proposal"]
        if item["item_type"] == "payment":
            tool, args = "execute_payment", {"kind": p["kind"], "ref_id": p["ref_id"], "account": p["account"]}
        else:
            tool, args = "execute_purchase_order", {"vendor_id": p["vendor_id"], "sku": p["sku"], "size": p["size"],
                                                    "qty": p["qty"], "account": p["account"]}
        try:
            execution = await mcp(tool, {**args, "approved_by": body.approved_by})
        except HTTPException as exc:
            append_event("approval_refused", approval_id=approval_id, ticket_id=item["ticket_id"],
                         approved_by=body.approved_by, reason=exc.detail, approval=item)
            raise

        item.update(status="approved", approved_by=body.approved_by, approved_at=now(), execution=execution)
        resolved = await maybe_resolve(state, item["ticket_id"])
        save_state(state)
    append_event("payment_approved", approval_id=approval_id, ticket_id=item["ticket_id"],
                 approved_by=body.approved_by, execution=execution, ticket_resolved=resolved)
    return {"approval": item, "execution": execution, "ticket_resolved": resolved}


@app.get("/api/cash")
async def cash():
    """Current checking balance from cash_accounts."""
    rows = await mcp("get_cash_balance", {"account": CASH_ACCOUNT})
    return rows[0]


@app.post("/api/reset")
async def reset():
    """Reset data/campus_customs_new.db from the original and clear the board (approvals, results). The audit trail is kept."""
    if RUN_LOCK.locked():
        raise HTTPException(409, "An agent run is in progress; reset after it finishes.")
    async with STATE_LOCK:
        reset_working_db()
        save_state(json.loads(json.dumps(EMPTY_STATE)))
    append_event("db_reset", source="api")
    return {"status": "reset", "cash": await cash(), "tickets": await mcp("list_tickets")}
