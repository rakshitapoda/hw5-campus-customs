"""Run the Campus Customs agent team over the open tickets.

    python -m backend.run_tickets              # full run: reset working DB, handle every open ticket
    python -m backend.run_tickets --ticket 102 # handle selected tickets only (no reset)

The Boss Agent starts each ticket and delegates to the rest of the team.
Every step is appended to output/audit_trail.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import uuid
from pathlib import Path

import backend.agents  # noqa: F401  (registers all five agents)
from backend.audit import append_event
from backend.models import TeamDeps, TicketBudget
from backend.team import MCP_TOOLSET, MODEL_NAME, run_agent

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIGINAL_DB = ROOT_DIR / "data" / "campus_customs.db"
WORKING_DB = ROOT_DIR / "data" / "campus_customs_new.db"
TICKET_TIMEOUT_SECONDS = 600  # wall-clock cap for one ticket, all agents included


def reset_working_db() -> None:
    """Rule 8: a complete run starts from a fresh copy of the original database."""
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)


async def main(ticket_ids: list[int] | None) -> None:
    run_id = uuid.uuid4().hex[:12]
    full_run = not ticket_ids
    if full_run:
        reset_working_db()
    append_event("run_start", run_id=run_id, model=MODEL_NAME, full_run=full_run, db_reset=full_run,
                 requested_tickets=ticket_ids)

    proposals: list[dict] = []  # shared across tickets so cash checks cover the whole run
    async with MCP_TOOLSET:
        if full_run:
            open_tickets = await MCP_TOOLSET.direct_call_tool("list_open_tickets", {})
            ticket_ids = [t["id"] for t in open_tickets]
        append_event("tickets_selected", run_id=run_id, ticket_ids=ticket_ids)

        for ticket_id in ticket_ids:
            deps = TeamDeps(run_id=run_id, ticket_id=ticket_id, agent="boss", chain=("boss",),
                            budget=TicketBudget(proposals=proposals))
            try:
                resolution = await asyncio.wait_for(
                    run_agent("boss", f"Handle ticket {ticket_id}.", deps), timeout=TICKET_TIMEOUT_SECONDS
                )
            except TimeoutError:
                append_event("ticket_timeout", run_id=run_id, ticket_id=ticket_id, limit_seconds=TICKET_TIMEOUT_SECONDS)
                print(f"\n=== Ticket {ticket_id}: FAILED (timed out after {TICKET_TIMEOUT_SECONDS}s)")
                continue
            except Exception as exc:  # recorded in the audit trail by run_agent; move on to the next ticket
                print(f"\n=== Ticket {ticket_id}: FAILED ({type(exc).__name__}: {exc})")
                continue
            print(f"\n=== Ticket {ticket_id}")
            print(json.dumps(resolution.model_dump(), indent=2))

    append_event("run_end", run_id=run_id, ticket_ids=ticket_ids)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ticket", type=int, action="append", help="Ticket id to handle (repeatable). Omit for a full run.")
    args = parser.parse_args()
    asyncio.run(main(args.ticket))
