# Homework 5: Campus Customs Multi-Agent Operations

# Problem 1: Create the AI_prompts.md log

## Assignment overview

My prompt:
now we will start homework 5, here is the synopsis: 

I am starting a coding assignment called Campus Customs Multi-Agent Operations. I want you to help me complete it one problem at a time. Do not build ahead or implement requirements from later problems unless I explicitly give them to you.

Here is the overall scenario and architecture for context:

Campus Customs Multi-Agent Operations is an agentic system that runs a campus shop. Open tickets represent tasks the shop needs to handle, such as customer orders, rent, unpaid bills, discount requests, inventory issues, and other operational needs.

The completed system will eventually have three connected components:

* an MCP server
* a FastAPI backend containing a multi-agent team
* a React dashboard where a human can observe agent activity and approve requests

The multi-agent team will eventually consist of:

* Boss Agent: Reads each ticket, determines which agent should work on it, delegates work, and makes final decisions.
* Inventory Agent: Checks inventory by SKU and size, identifies shortages, and determines which vendor can restock products.
* Accounting Agent: Monitors cash and invoices, checks margins, and prepares payments or purchase orders for human approval.
* Facilities Agent: Handles shop-space matters such as leases and rent.
* Customer Service Agent: Drafts customer-facing messages.

The agents have full connectivity, meaning any agent may delegate a task to any other agent when help is needed.

Database

The provided original SQLite database is:

data/campus_customs.db

It contains these tables:

desk
tickets
inventory
pricing
vendors
leases
cash_accounts
payments
invoices

The original database must remain untouched.

Create/use a working copy named:

data/campus_customs_new.db

The MCP server and backend should eventually operate on this working copy because tools will modify the database as tickets are resolved.

Important business rules

1. desk.date_today represents today’s date for the shop. Use this value rather than the computer’s actual current date when determining whether something is overdue.
2. Vendor lead times must come from the vendors table.
3. A vendor will not ship new products while it has an open unpaid invoice.
4. Every payment requires human approval. Never execute a payment automatically.
5. When an approved payment is eventually made, the appropriate database records must also be updated.
6. A payment must be refused if there is insufficient cash. Cash balances may never become negative.
7. Cash only flows out in this assignment. Revenue is not modeled, so do not create incoming cash transactions.
8. Before a complete ticket-resolution run, the working database should be reset from the original database.
9. Do not actually email customers or contact vendors. Customer/vendor communications should only be drafted and displayed/stored on the board.

AI/model requirements

AI calls must use my PORTKEY_API_KEY.

For this assignment, every agent must use only gpt-6-luna through Portkey. Do not introduce another model anywhere in the project. Do not add fallback models or use a different model for testing.

How I want you to work

I will give you the assignment problems one at a time.

For each problem:

1. First inspect the existing project/repository and understand what is already implemented.
2. Read the specific problem I give you carefully.
3. Implement only what is required for that problem.
4. Preserve all functionality completed in earlier problems.
5. Do not anticipate or implement later problems unless necessary for the current requirement.
6. Prefer simple, readable solutions over unnecessary complexity.
7. Do not modify data/campus_customs.db.
8. Use data/campus_customs_new.db whenever the assignment requires a mutable working database.
9. Follow the business rules above exactly.
10. After making changes, run appropriate tests/checks to verify that the current problem works.
11. Tell me exactly which files you created or changed and briefly explain what you did.
12. Tell me if there is anything I need to run or verify manually before moving to the next problem.

Result:
Logged the synopsis and checked the project. `hw-5/` was empty except for this file, so there was nothing to build on yet. No code was written, per the instruction not to build ahead.

---

## Problem 1 follow-up: Inspect the provided data and set the log format

My prompt:
there is the data folder in the hw5, unzip that and read the documents. keep the ai prompts upadted as i work, and in each one include the problem number and title, the prompt i typed and the result and anythign else you need to include in the md file

Result:
- There was no zip to extract. `data/` holds only `campus_customs.db`, which is already unpacked.
- Read every table in read-only mode (`sqlite3 -readonly`). The original database was not modified (SHA-1 `f447ca6a2766a90f3c1f81215c8f774ab109ea4c`).
- The 9 tables match the synopsis: desk (1 row), tickets (3), inventory (10), pricing (4), vendors (3), leases (1), cash_accounts (1), payments (0), invoices (1).

Key facts from the data:
- Shop "today" (`desk.date_today`) = 2026-08-31.
- Cash: `checking` = $3,400.00.
- Open tickets:
  - 101 customer_order: Tauhid Zaman wants CC-TEE-WHITE size S x1. Stock for S = 0. The ticket links to invoice 501.
  - 102 rent_notice: Elm City Properties, lease 1 (Chapel Street shop), $2,400 due 2026-09-02.
  - 103 price_override: Yale AI Club wants 20 CC-HOOD-NAVY size M with a bulk discount. Stock for M = 8. Unit cost $22, list price $58.
- Invoice 501: Bulldog Print Co (vendor 1), $840, due 2026-08-28, status `open`. It is overdue relative to 2026-08-31, so vendor 1 won't ship until it's paid (rule 3).
- Vendor lead times: Bulldog Print Co 5 days (apparel), Elm City Gifts 3 days (mugs/small goods), QuickShip CT 1 day (local courier).
- Paying both invoice 501 and the rent ($3,240) would leave $160. That's allowed because the balance stays non-negative (rule 6).

Notes:
- No code or files created besides this log.

---

## Problem 1 follow-up: Label this section as Problem 1

My prompt:
prblem one was the creation of the ai prompts md file

Result:
Renamed the first two section headings in this file so they fall under Problem 1. Before, they were "Assignment Overview" and "Setup: Inspect the provided data". The prompts and results in those sections were not changed. No code or data was touched.

---

# Problem 2: Study the database, create the working copy, and start the harness

My prompt:
for problem 2:  

want you to study the campus customs database. open data/campus_customs.db and look through every table and all of the fields. make a copy of the original database called data/campus_customs_new.db since we will use and update that copy in the later problems. do not make any changes to the original database.

also look at the three open tickets and understand how the information in those tickets connects to the other tables in the database.

then create output/harness.md. for every table in the database, list all of its fields and add a short explanation of why that table is important for the agents. we will continue adding to this harness file in the later problems.

Result:
- Created `data/campus_customs_new.db` as a byte-for-byte copy (`cp`) of `data/campus_customs.db`. Both have SHA-1 `f447ca6a2766a90f3c1f81215c8f774ab109ea4c`, and a table-by-table row comparison showed all 9 tables identical.
- The original was only opened read-only (`sqlite3 -readonly`). Its checksum is unchanged after the work, and `PRAGMA integrity_check` returned `ok`.
- Created `output/harness.md` with:
  - a Databases section explaining that the original is read-only and the working copy is mutable/resettable
  - one section per table (desk, tickets, inventory, pricing, vendors, leases, cash_accounts, payments, invoices), each with every field (name, type, meaning) and why the table matters to the agents
  - a "How the open tickets connect to the database" table for tickets 101, 102, and 103, plus the cash constraint
- Verification: a script compared every column from `PRAGMA table_info` against harness.md. All 9 tables and every field are documented (missing=0).

Ticket connections found:
- 101: tee size S has 0 in stock. The ticket links to invoice 501 (Bulldog Print Co, $840, overdue since 2026-08-28), which blocks the apparel restock until it's paid. After payment, restock takes 5 lead days.
- 102: matches lease 1 ($2,400 to Elm City Properties, due 2026-09-02 = today + 2 days).
- 103: only 8 of 20 hoodies (size M) in stock. The restock of 12 is blocked by the same invoice 501. Cost is $22 vs. a $58 list price, which limits the discount.
- Cash: $3,400. Invoice + rent = $3,240, leaving $160.

Files created: `data/campus_customs_new.db`, `output/harness.md`.

Notes:
- Nothing from later problems (MCP server, backend, agents, frontend) was built.

---

# Problem 3: Build the Campus Customs MCP server

My prompt:
okay now, 

i want you to build the mcp server for campus customs. create it inside mcp_server/ using fastmcp and have it work with data/campus_customs_new.db. every agent will eventually use the tools from this server.

for now, create three tools that will be needed to handle the tickets we found in the database. give the tools clear names and make sure they only use information that actually exists in the database. do not invent any data.

then add the mcp server to this project in claude code so you can call the tools. save the mcp connection configuration in .mcp.json at the project root. test each of the three tools to make sure they work correctly.

Result:
- Created a `.venv` (Python 3.13.15) and installed `fastmcp` 4.1.0 (mcp 2.3.0).
- Created `mcp_server/server.py`, a FastMCP server named `campus-customs` (stdio) with three read-only tools on `data/campus_customs_new.db`:
  - `check_inventory(sku, size)`: inventory row plus `in_stock`, `unit_cost`, `list_price` (pricing table). For tickets 101 and 103.
  - `get_lease(lease_id)`: lease row plus `days_until_due` / `is_overdue` measured from `desk.date_today`. For ticket 102.
  - `check_vendor_status(vendor_id=None)`: vendor specialty and `lead_days`, open invoices with `days_overdue`, `open_balance`, and `can_ship` (False while an invoice is open, rule 3). For restocking in tickets 101 and 103.
  - Unknown records raise a `ToolError` (e.g. "Lease 99 does not exist."). No defaults or made-up values. If the working DB is missing, the server errors instead of falling back to the original.
- Created `.mcp.json` at the project root, registering `campus-customs` as a stdio server (`.venv/bin/python mcp_server/server.py`).
- Created `requirements.txt` (`fastmcp>=4.1`) and `.gitignore` (`.env`, `.venv/`, `__pycache__/`, `.DS_Store`).
- Added an "MCP server tools" section to `output/harness.md`.

Tests (MCP client started the server with the exact command from `.mcp.json`, over stdio):
- list_tools → `check_inventory`, `get_lease`, `check_vendor_status`
- `check_inventory(CC-TEE-WHITE, S)` → qty 0, in_stock false, cost 8.0, list 28.0 ✔ matches DB
- `check_inventory(CC-HOOD-NAVY, M)` → qty 8, Aisle A, cost 22.0, list 58.0 ✔
- `get_lease(1)` → Chapel Street shop, Elm City Properties, $2400, due 2026-09-02, days_until_due 2, not overdue ✔
- `check_vendor_status(1)` → Bulldog Print Co, 5 lead days, invoice 501 $840 overdue 3 days, can_ship false ✔
- `check_vendor_status()` → all 3 vendors. Elm City Gifts and QuickShip CT have no open invoices, so can_ship true ✔
- Error cases: size XXL → "Sizes on record: L, M, S, XL"; lease 99 and vendor 42 → "does not exist" ✔
- Both database checksums were unchanged after testing (`f447ca6a…`). The tools are read-only.

Notes:
- The test harness sat in a scratch folder outside the project, so no test files were added to hw-5.
- Turned off the FastMCP startup banner (`show_banner=False`) to keep the stdio output clean.
- This Claude Code session was opened before `.mcp.json` existed, so the tools appear as Claude Code tools only after a reload in the hw-5 folder and approval of the project server.

---

# Problem 4: Finish testing the MCP server (smoke test evidence)

My prompt:
now for problem 4, i want to finish testing the mcp server we created. make sure the mcp server is connected to this project so you can call the tools, with the connection saved in .mcp.json at the project root.
test each of the three mcp tools we created. save the results in output/mcp_smoke.json.
for each tool, include:

* the prompt used to test it
* the tool name
* the tool output

make sure the outputs match the actual values in data/campus_customs_new.db.
if the mcp connection and testing were already done from the previous step, don’t redo anything unnecessarily. just verify that it works and create or update output/mcp_smoke.json with all of the required evidence.

Result:
- Nothing was rebuilt. `mcp_server/server.py` and `.mcp.json` from Problem 3 were reused unchanged.
- Connection check: the current Claude Code session started in the home folder before `.mcp.json` existed, so the `campus-customs` tools were not loaded as native tools (ToolSearch found none). To verify the connection, an MCP client started the server with the exact `command` and `args` from `.mcp.json` over stdio, the same way Claude Code launches it. `list_tools` returned all three tools.
- Created `output/mcp_smoke.json` with 4 tests covering all 3 tools (check_inventory was tested for both ticket 101 and ticket 103). Each test records the natural-language prompt, the tool name, the arguments, the full tool output, and a `db_verification` block (the SQL run against `data/campus_customs_new.db`, the expected values, `matches_db`, and any mismatches).
- Results, all matching the DB (`all_match_db: true`):
  - check_inventory(CC-TEE-WHITE, S) → qty 0, Aisle B, cost 8.0, list 28.0
  - check_inventory(CC-HOOD-NAVY, M) → qty 8, Aisle A, cost 22.0, list 58.0
  - get_lease(1) → Elm City Properties, $2400, due 2026-09-02, date_today 2026-08-31, 2 days until due
  - check_vendor_status(1) → Bulldog Print Co, 5 lead days, open invoice 501 ($840, 3 days overdue), can_ship false
- Both database checksums are unchanged (`f447ca6a…`).

Files created: `output/mcp_smoke.json`.

Notes:
- The smoke-test script ran from a scratch folder outside the project, so no extra files were added to hw-5.
- To see the tools natively in Claude Code: open hw-5 as the workspace, start a new session, and approve the `campus-customs` server from `.mcp.json` (check with `/mcp`).

---

# Problem 5: Build the PydanticAI agent team, expand the MCP tools, audit trail, harness and README

My prompt:
now 

now i want to build the agent team for campus customs using pydanticai. create the 5 agents: boss, inventory, accounting, facilities, and customer service. give each agent its own prompt and model, and make sure all of the agents can delegate work to each other.

put the prompts in backend/prompts/ with one file per agent, put the data types in backend/models.py, and keep the agent files under backend/. write detailed prompts for each agent based on its role and the shop rules it needs to follow.

use my PORTKEY_API_KEY and only gpt-6-luna for every agent.

add any additional tools the agents need to the mcp server so they can handle the open tickets. all shop information should come through the mcp server using data/campus_customs_new.db. don’t create another way for the agents to access the shop data or make up information that isn’t in the database.

also have the agents append their activity to output/audit_trail.json. record each step of the agent loop with enough information that we can understand what happened later. make sure it appends to the existing file instead of clearing it on each run.

update output/harness.md to include all 5 agents and all of the mcp tools, including any new tools you add. for each tool, include which database table it uses. add a short safety section with guardrails for agents working with real customers and money, and limits to prevent excessive token usage.

finally, update mcp_server/README.md so the tool list matches all of the tools that are currently in the mcp server.

Result:
Files created:
- `backend/__init__.py`
- `backend/models.py`: data types: `AgentName`, `PaymentRequest`, `PurchaseOrderRequest`, `MessageDraft`, `AgentReport` (specialist output), `TicketResolution` (boss output), `TicketBudget`, `TeamDeps`.
- `backend/team.py`: shared setup:
  - `build_model()` creates an `OpenAIResponsesModel("gpt-6-luna")` through Portkey with `PORTKEY_API_KEY`. No other model or fallback.
  - One shared `MCPToolset` connection to `mcp_server/server.py`.
  - The `delegate_task` tool (full connectivity).
  - The audited `run_agent` loop.
  - A proposal output validator.
  - Token/loop limit constants.
- `backend/agents/{boss,inventory,accounting,facilities,customer_service}.py` + `__init__.py`: one file per agent. Each builds its own model instance, loads its own prompt, and gets a filtered subset of the MCP tools.
- `backend/prompts/{boss,inventory,accounting,facilities,customer_service}.md`: detailed role prompts with the shop rules each agent must follow.
- `backend/audit.py`: append-only writer for `output/audit_trail.json`.
- `backend/run_tickets.py`: CLI. `python -m backend.run_tickets` does a full run (resets the working DB from the original per rule 8, gets the open tickets via MCP, and the boss handles each one). `--ticket N` handles selected tickets without a reset.
- `mcp_server/README.md`: the full tool list (11 tools, arguments, returns, tables).
- `.env.example`: placeholders only.
- `output/audit_trail.json`: created by the runs and appended to on each run.

Files changed:
- `mcp_server/server.py`: added 8 tools:
  - `get_shop_date`, `list_open_tickets`, `get_ticket`, `get_invoice`, `get_cash_balance`, `check_margin`
  - `prepare_payment` and `prepare_purchase_order`. These validate and return a proposal (`awaiting_human_approval` / `blocked` / `refused`). They never write to the DB or execute a payment.
  - Total: 11 tools. All are read-only on `data/campus_customs_new.db`.
- `output/harness.md`: replaced the MCP tools section with all 11 tools (inputs, returns, tables used, which agents). Added the Agent team, Audit trail, and Safety and guardrails sections (money, customers, data integrity, token/loop limits table).
- `requirements.txt`: added `pydantic-ai-slim[openai,mcp]` and `python-dotenv`.

Verification:
- An offline check through MCP showed:
  - `prepare_payment(invoice 501)` → $840 awaiting approval.
  - `prepare_purchase_order(vendor 1, hoodie M x12)` → blocked by invoice 501.
  - `prepare_payment(rent, pending_total=1200)` → refused (balance would be -$200).
  - `check_margin` 20% off → $46.40, not below cost.
  - Each agent sees only its tool subset.
- A script confirmed the README and harness tool lists match the server's 11 tools exactly.
- Final live full run (the 5th live run; earlier runs are described under "Problems hit and fixes"), all three tickets, exit 0, 109 audit events:
  - 101 → `awaiting_approval`. Invoice 501 payment ($840) awaiting approval. A 1-unit tee PO ($8) is `blocked` by invoice 501. A customer draft for Tauhid Zaman promises no date.
  - 102 → `awaiting_approval`. Facilities verified the notice against lease 1, and accounting prepared the $2,400 rent payment (pending_total $840 included in the cash check).
  - 103 → `needs_human`. Accounting ran check_margin at 10/15/20% off ($52.20 / $49.30 / $46.40, all above the $22 cost). 8 of 20 in stock, and the 12-unit restock is blocked by invoice 501. The draft to Yale AI Club promises no discount.
  - Usage per ticket: 10–15 model requests and about 21k–38k tokens, well under the limits (40 requests / 250k tokens).
- The audit trail grew 174 → 281 → 390 events across runs. It appends and never clears.
- The original DB checksum is unchanged (`f447ca6a…`).

Problems hit and fixes:
1. The first live run failed with HTTP 400: this Portkey/Azure route rejects function tools on chat completions while reasoning is on. Fix: switched to `OpenAIResponsesModel` (Responses API), still `gpt-6-luna` only.
2. Ticket 101 reported a "duplicate" invoice payment that didn't exist: the agent misread the "already prepared" note listing its own proposal. Fix: proposals are tagged with ticket and agent, de-duplicated on record, and the note explains they are the same item.
3. One run hung for about 15 minutes on a model request (no HTTP timeout), and Portkey was replaying cached replies from the previous run. Fix: 120 s request timeout, 1 retry, a 600 s per-ticket limit, and the `x-portkey-cache-force-refresh` header. That run was stopped manually, and a `run_aborted` event was logged for it.
4. In one run accounting didn't prepare the rent because it wasn't overdue yet, and skipped margins because no target price was given. Fix: the prompts now say to prepare valid rent notices for approval ahead of the due date, to check standard discount levels when no price is named, and to prepare a PO for any shortage even if blocked.

Notes:
- Payments are never executed, and the `payments` table is untouched. Executing approved payments and showing drafts on a board are left for later problems.
- LLM output varies between runs. For example, in the final run the hoodie restock PO for ticket 103 wasn't prepared, though the blocker was reported correctly.
- The key was read from the shell environment and never printed. There is no `.env` file in the project.

---

# Problem 6: Plan expected agent behavior per ticket (desk_tickets.html)

My prompt:
for problem 6 now i want to plan what i expect the agent team to do for each of the three open tickets before we build the backend and actually run the agents.

create output/desk_tickets.html as a page i can open in my browser. make separate tabs for tickets 101, 102, and 103. also add cash and reflection tabs for later, but leave those blank or just say coming later.

for each ticket, add an expected section based on the actual ticket and database information. leave space for an actual section that we will fill in later after rununing the agents.

in the expected section for each ticket, explain:

* which agent the boss should call first and why
* all of the delegations i expect between agents
* which mcp tools i expect them to use

make the plan specific to each tcket. don’t just send every agent to every ticket. only include the agents that actually make sense for that ticket based on what we know from the database and the roles of each agent.

Result:
- Created `output/desk_tickets.html`: a single self-contained page (inline CSS and JS, no external files or fetches) with a white and Yale-navy design. It has 5 tabs: Ticket 101, 102, 103, Cash ("Coming later."), and Reflection ("Coming later.").
- Each ticket tab has: a facts card from the database, an **Expected** section (Boss's first call and why, numbered delegation flow, a table of expected MCP tool calls with expected results, expected outcome, and which agents are *not* called and why), and a dashed **Actual** section with empty slots (first call, delegations, tools used, outcome, expected vs. actual) to fill in later.
- Plans per ticket:
  - 101 (customer_order): Boss → **Inventory** first (stock by SKU and size decides everything). Inventory → Accounting (invoice #501 payment of $840 for approval, plus a 1-unit PO of $8 that should be blocked). Boss → Customer Service (draft to Tauhid, no date). Facilities is not called.
  - 102 (rent_notice): Boss → **Facilities** first (verify the notice against lease #1 before preparing any money). Facilities → Accounting (`prepare_payment("rent", 1, pending_total=840)` → awaiting approval, $160 left). Inventory and Customer Service are not called (no product; the landlord isn't a customer and needs no reply).
  - 103 (price_override): Boss → **Inventory** first (only 8 of 20 in stock, which frames the discount question). Boss → Accounting (check_margin at 10/15/20% off, plus a 12-unit PO of $264 that should be blocked, and no duplicate #501 payment). Boss → Customer Service (draft to Yale AI Club, no discount or date promised). Facilities is not called. Includes a cash warning: even after #501 is paid, $3,400 − $840 − $2,400 = $160 < $264, so a human must choose between rent and the full restock.
- Verification:
  - Every number on the page was checked against live MCP tool output:
    - margins 10% → $30.20 / $604 / 57.85%, 15% → $27.30 / $546 / 55.38%, 20% → $24.40 / $488 / 52.59%, break-even 62.07% off
    - hoodie PO → blocked, $264, balance_after −$104
    - tee PO → blocked, $8, arrival 2026-09-05 if ordered today
    - rent with pending $840 → awaiting approval, $160 left
  - HTML parser check: no unclosed or mismatched tags. All 5 tab buttons match their 5 panels, and there are no external references.

Notes:
- The Actual sections are deliberately blank; Problem 5's test-run results were not copied in, per the instruction to fill them in after running the agents.
- Chrome isn't installed, so no screenshot was taken. The structure was checked programmatically instead.

---

# Problem 7: FastAPI backend routes for the dashboard

My prompt:
now ow i want to build the backend routes for the campus customs dashboard. use fastapi in backend/main.py.

add routes that can:

* return the three tikcets and whether each one is open or resolved
* take a ticket id and run the agent team on that ticket
* return recent agent activity, including what each agent said and which tools they used
* approve a payment or purchase after a human approves it. the agents should only prepare the payment, and this route should be what actually changes the cash balance
* return the current checking balance from cash_accounts
* reset the working database back to the original values for a fresh run

make sure this works with everything we already built and follows the shop rules, especially the human approval requirement for payments.

the backend shld be able to run from the backend/ folder using uvicorn main:app --reload --port 8000.

also update output/harness.md with each backend route, including the url and a short description of what it does.

Result:
Files created:
- `backend/main.py`: FastAPI app. It runs from `backend/` with `uvicorn main:app --reload --port 8000` (adds the project root to `sys.path`, so the existing `backend.*` modules import unchanged). One MCP connection is opened for the app's lifetime (lifespan). CORS is allowed for local dev origins. Routes:
  - `GET /api/tickets`: all tickets, open/resolved status, latest agent result, approval counts
  - `POST /api/tickets/{id}/run`: starts the agent team in the background (202 + run_id). 404 for an unknown ticket; 409 if resolved or another run is in progress
  - `GET /api/runs/{run_id}`: run status and the Boss's resolution
  - `GET /api/activity`: recent audit events, newest first (agent, what it said, tools + args, delegations, approvals)
  - `GET /api/approvals`: payments/POs the agents prepared (pending / blocked / refused / approved)
  - `POST /api/approvals/{id}/approve` with `{"approved_by": ...}`: **the only route that moves money**
  - `GET /api/cash`: checking balance
  - `POST /api/reset`: copies the original DB over the working copy and clears the board state (audit kept)
- `output/board_state.json`: created by the backend. Holds approval items and each ticket's latest result (decision, message drafts). Cleared on reset.

Files changed:
- `mcp_server/server.py`: added 4 backend-only tools (15 total). No agent has them (verified: every agent's tool list contains none of them).
  - `list_tickets`
  - `update_ticket_status`
  - `execute_payment`: one transaction. Requires `approved_by`, refuses if the invoice isn't open or cash would go negative, inserts a `payments` row with paid_at = desk.date_today, marks the invoice `paid` (or moves `leases.next_due` forward one month for rent), and debits cash.
  - `execute_purchase_order`: refuses while the vendor has an open invoice or if cash would go negative. Records a payment and debits cash. Stock is unchanged until delivery.
- `backend/models.py`: added `Approval`, `ApproveRequest`, `RunStatus`.
- `backend/team.py`, `backend/audit.py`: made `proposal_key` and `load_events` public for reuse.
- `output/harness.md`: new Backend routes section (method, URL, description for all 8 routes). Added the 4 new tools to the MCP table with tables used. Added the new audit events (`payment_approved`, `approval_refused`, `db_reset`). Safety section updated: money moves only through the approve route.
- `mcp_server/README.md`: tool list now matches all 15 tools.
- `requirements.txt`: added `fastapi`, `uvicorn[standard]`.

How the approval rule is enforced:
- Agents only have `prepare_*` (no writes). Their prepared items become approval records.
- Only `pending` items can be approved, each once. Blocked, refused, and already-approved items get 409.
- `approved_by` is required (422 if empty), and the execute tool re-checks cash, invoice status, and vendor blocks live.
- Pending items are fed into the next agent run, so agents don't re-prepare them and the cash check counts them.

Verification (server started from `backend/` with the exact uvicorn command, real gpt-6-luna runs):
- Write tools first tested on a throwaway DB copy:
  - no approver → refused
  - PO while invoice 501 open → refused
  - pay 501 → paid, $3,400 → $2,560
  - pay 501 again → refused
  - rent → paid, next_due 2026-10-02, $160 left
  - hoodie PO $264 → refused (insufficient cash)
  - tee PO $8 → ordered, arrival 2026-09-05
- API:
  - reset → $3,400, all tickets open
  - unknown ticket run → 404
  - unknown approval → 404
  - empty approver → 422
- Ran ticket 102 via the API. While it ran, a second run → 409 and reset → 409. The agents prepared the $2,400 rent payment. Approved by "Rakshita Podagatlapalli" → cash $3,400 → $1,000, `payments` row written with approved_by, lease next_due → 2026-10-02, ticket 102 → resolved. Approving again → 409. Running the resolved ticket → 409.
- Ran ticket 101 via the API → invoice 501 payment pending, tee PO blocked, draft to Tauhid Zaman stored on the board. Approving the blocked PO → 409. Approving the invoice → cash $1,000 → $160, invoice 501 `paid`. Ticket 101 stays open (its PO is still blocked).
- `/api/activity` showed agent text, decisions, tool calls, delegations, and "Approved by …" events.
- Reset → cash $3,400, 0 payments, invoice open, next_due 2026-09-02, approvals cleared, and the working DB checksum is identical to the original again (`f447ca6a…`).
- A script confirmed the harness and README list all 15 MCP tools, and the harness lists all 8 routes.

Notes:
- Agent runs take a few minutes, so `POST /run` returns immediately and the dashboard polls `/api/runs/{run_id}`. Only one run happens at a time because all runs share one database.
- A ticket is marked resolved automatically when the Boss says `resolved`, or when the Boss said `awaiting_approval` and a human has approved every item for that ticket.
- The test server was stopped afterwards (the "exit 144" was the manual stop).

---

# Problem 8: React + Vite + TypeScript agent dashboard (frontend/) and design.md

My prompt:
now i want to build the frontend agnet dashboard in frontend/ using react, vite, and typescript. connect it to the backend we built at http://localhost:8000.

the dashboard should:

* show all three tickets
* let me select one ticket and start the agent team on it
* show each agent and what they are doing/saying while the ticket is running
* show when a ticket is resolved
* show a short summary of what each agent did for that ticket
* let me approve a payment or purchase when human approval is needed
* show the current checking balance and update it after an approved payment

make the dashboard look polished and creative, like an actual operaitons desk someone would want to use. make the agents visually easy to tell apart and make ticket status, approvals, and the cash balance easy to understand.

make sure the backend allows requests from the vite frontend, usually http://localhost:5173, and that the frontend works with the routes we already created. it should run with npm run dev.

also creat output/design.md explaining the dashboard design choices, including the layout, how the agents look different, how resolved tickets and cash are displayed, and why you made those choices.

Result:
Files created:
- `frontend/`: scaffolded with `npm create vite@latest` (react-ts template, Vite 8, React 19, TypeScript 6). Demo assets removed. Runs with `npm run dev` on port 5173.
  - `src/types.ts`: TypeScript shapes of every backend response.
  - `src/api.ts`: typed client for all 8 routes. Base URL `VITE_API_URL`, default `http://localhost:8000`. Shows the backend's `detail` message on errors.
  - `src/agents.ts`: agent identities (color, role, monogram), plain-language tool labels, and `deriveAgentStates()`, which replays a run's audit events into each agent's live phase (working / waiting / done / error / not on this ticket).
  - `src/format.ts`: money/time formatting and desk status (not started, agents working, needs your approval, blocked, needs a decision, resolved).
  - `src/components/`: `TopBar`, `TicketQueue` (ticket stubs + RESOLVED stamp), `TicketDetail` (header with Start button, Boss's decision with drafts), `AgentFloor` (5 agent stations), `ActivityFeed` (live feed), `AgentSummaries` (what each agent did), `CashCard` (balance, delta flash, cash bar), `ApprovalTray` (payment slips + confirm dialog), `AgentBadge` (icons/badges/chips).
  - `src/App.tsx`: state and polling. Tickets/approvals/cash every 5 s, the live run's activity every 1.5 s, and run status every 2 s until the run finishes, then a refresh and a toast.
  - `src/index.css`: the full design (navy frame, light desk, status color language, agent colors, responsive breakpoints, reduced-motion support).
  - `public/favicon.svg`, `index.html` title, `vite.config.ts` (port 5173), `.env.example`, `README.md` (how to run).
- `output/design.md`: design rationale covering layout, agent identities, status colors, resolved tickets, cash display, approvals, and other choices.

Files changed:
- `backend/main.py`: CORS now allows `http://localhost:5173` / `127.0.0.1:5173`, plus any localhost port via `allow_origin_regex` (in case Vite picks the next free port).

Verification:
- `npm run build` (tsc + vite) passes. Fixed two type errors along the way. `oxlint` is down to 1 warning (the fetch-on-mount polling effect, which legitimately syncs with the backend).
- CORS: preflight and GET with `Origin: http://localhost:5173` return `access-control-allow-origin: http://localhost:5173`.
- End-to-end in a real headless browser (Playwright Chromium, installed in a scratch folder outside the project) against the live backend and gpt-6-luna:
  - opened the dashboard (3 tickets)
  - selected #102 and clicked **Start agent team**
  - mid-run: Boss "Waiting", Facilities and Accounting "Done", Inventory and Customer Service "Not on this ticket"
  - after the run: "Needs your approval", with a $2,400 rent slip in the sign-off tray
  - entered the approver name, clicked Approve, then **Approve & pay** in the confirm dialog
  - cash went **$3,400.00 → $1,000.00** with a −$2,400 flash, and the ticket was stamped **Resolved**
  - no browser console errors
- Screenshots reviewed at 1600px, 1100px, and 420px. Fixed afterwards: speech bubbles cut text mid-line, horizontal overflow on mobile (scrollWidth is now 420 at 420px), the RESOLVED stamp overlapping the type label, and a resolved ticket still showing only the stale "awaiting approval" sentence (it now shows a green "Resolved · $2,400.00 approved by …" bar).
- Afterwards: reset the desk through the API (cash $3,400, working DB checksum = original), stopped both servers, and removed `frontend/dist`.

Notes:
- The dashboard only uses the existing routes. Money moves only through the approve route, which needs a name and a confirm step.
- `frontend/node_modules` is local only and is git-ignored by the Vite template's `.gitignore`.

---

# Problem 9: Full run: resolve all three tickets, cash tab, resolved outputs, finished harness

My prompt:
ow i want to do a full run and resolve all three tickets. first reset data/campus_customs_new.db back to the original values so we start clean, and record the starting checking balance.

then run tickets 101, 102, and 103 through the agent team until each one is resolved. make sure any payments or purchases that require human approval are handled through the approval process we built and that the cash balance is updated correctly.

updaet output/desk_tickets.html for each ticket by filling in the actual section with which agents worked on it, what they delegated, and which tools they used. keep the expected sections from problem 6 so i can compare expected vs actual.

also fill in the cash tab with:

* the starting checking balance after the reset
* the cash change for each ticket, including what payment or purchase caused it and the dollar amount
* the ending checking balance

make sure the ending balance exactly matches cash_accounts in the working database.

create output/resolved_tickets.json with each ticket's id, final status, short outcome, what each agent contributed, and any human approvals.

also create output/resolved_board.html with a screenshot of the react dashboard for each resolved ticket 101, 102, and 103.

append the real agente runs to output/audit_trail.json instead of overwriting it.

finally, finish output/harness.md so it includes the database tables, all mcp tools, all 5 agents, api routes, dashboard, and safety rules. verify all of the outputs and cash math before finishing.

Clarifying questions Claude asked (cash can't cover everything: $840 + $2,400 + $8 + $264 = $3,512 > $3,400), and my answers:
- Ticket 103 discount: "10% off — $52.20 (Recommended)"
- Ticket 103 shortage: "Sell the 8 in stock, no restock (Recommended)"

Result:
New feature needed to resolve 103 (a human judgment call):
- `POST /api/tickets/{id}/decision` in `backend/main.py` (+ `DecisionRequest` in `backend/models.py`). Records a human decision in `board_state.json`, logs a `human_decision` audit event, and adds it to the Boss's prompt on the next run. It never moves money.
- `backend/prompts/boss.md`: new "Human decisions" section (treat recorded decisions as final for judgment calls, within the shop rules).
- Dashboard: "Your decision" box for `needs_human` tickets (`TicketDetail.tsx`, `api.ts`, `types.ts`, `App.tsx`, `index.css`). The RESOLVED stamp moved inline into the stub footer so it no longer covers the agent chips.

The full run (through the API on the live backend, gpt-6-luna):
1. `POST /api/reset` → **starting checking balance $3,400.00**, 0 payments, working DB byte-identical to the original. The audit trail had 496 events.
2. Ticket 101, run 1: Boss→Inventory, Boss→Accounting, Boss→Customer Service. Invoice #501 payment pending, tee PO blocked. **Approved invoice #501 → $840.00, $3,400 → $2,560** (payment #1, invoice → paid).
3. Ticket 101, run 2: the PO was now prepared (vendor can ship). **Approved the tee PO → $8.00, $2,560 → $2,552** (payment #2, arrival 2026-09-05). Ticket 101 → resolved.
4. Ticket 102: Boss→Facilities→Accounting, rent prepared. **Approved rent → $2,400.00, $2,552 → $152** (payment #3, lease next_due → 2026-10-02). Ticket 102 → resolved.
5. Ticket 103, run 1: margins at 10/15/20% off. The 12-unit PO ($264) was **refused** for insufficient cash ($152). Status needs_human.
6. Recorded the human decision (10% off at $52.20 on the 8 in stock, no restock). Ticket 103, run 2 → **resolved**, no money moved.
7. **Ending checking balance $152.00** = `cash_accounts.checking` = $3,400 − $840 − $8 − $2,400. The `payments` table has 3 rows totalling $3,248, all with approved_by "Rakshita Podagatlapalli".

Approvals were made by Claude through the approval route, as instructed in this prompt, with my name as approver.

Files created / updated:
- `output/desk_tickets.html`: the Actual section for each ticket (final status, agents, who the Boss called first, run-by-run delegations with task text, every MCP tool call with real arguments, the Boss's decision, the approvals table, and an expected-vs-actual comparison with match/differs badges). The Cash tab has the start, total paid out, and end balance, the change by ticket, the ledger in payment order with before/change/after and approver, and the math check against `payments` and `cash_accounts`. The Expected sections are byte-identical to Problem 6 (verified). The Reflection tab still says "Coming later".
- `output/resolved_tickets.json`: start/end/paid-out balances, and per ticket: id, type, final_status, outcome, agent runs (delegations, tools, usage), agent_contributions, human_approvals (amount, approver, payment id, balance before/after), not_approved items, human_decisions, cash_change, and message_drafts.
- `output/resolved_board.html`: self-contained (images embedded as base64), with Playwright screenshots of the React dashboard for resolved tickets 101, 102, and 103, plus the cash summary.
- `output/audit_trail.json`: **appended** 200 events (496 → 696). Timestamps are monotonic and the earlier events are untouched.
- `output/harness.md`: added a contents and system overview, the decision route, the `human_decision` audit event, a **Dashboard** section, the human-decision safety rule, and a "Full run results and output files" section.

Verification:
- The generator script asserts that each approval's balance_before/after chains from $3,400 to $152, that the ending balance equals `cash_accounts`, that total paid out equals the `payments` sum, and that the payment count matches. All passed.
- `resolved_tickets.json`: all 3 resolved, cash changes sum to −$3,248 = the payments total, and start − paid = end = DB.
- harness.md was checked by script against the code and DB: all 9 tables with every field, all 15 MCP tools, all 9 routes, all 5 agents, plus the Dashboard and Safety sections.
- HTML parser: desk_tickets.html is well-formed with no "To be filled in" left. In resolved_board.html all 3 images load. No page errors.
- The original DB checksum is unchanged (`f447ca6a…`). The working DB is intentionally left at the final state (cash $152).

Expected vs. actual differences (documented in the page):
- 101: the Boss delegated to Accounting directly rather than through Inventory, and it took 2 runs.
- 102: pending_total was 0 rather than 840, because invoice #501 was already paid.
- 103: in run 1 the Boss delegated to Accounting and Inventory together. The PO was refused for cash rather than blocked by the invoice, so the cash warning from Problem 6 came true. Accounting made one probe check_margin call at $0, and in run 2 it checked margins at qty 20 rather than 8 (the per-unit margin is identical).

Notes:
- Selling the 8 hoodies isn't written to the DB: there is no sales table, and revenue isn't modeled (cash only flows out).
- Both servers were stopped after the screenshots.

---

# Problem 10: Reflection tab in desk_tickets.html

My prompt:
now i want to complete the reflection for the project. open output/desk_tickets.html and fill in the reflection tab. base all of the answers on what actually happened in our app and the three tickets we ran, including the expected vs actual sections and the cash tab. don't give generic answers.

in the reflection, answer:

* how well the agents performed on each of the three tickets and why
* for each ticket, how the actual run compared to the expected plan i made earlier
* which parts of this project would have been simpler to handle with one agent using tools instead of multiple agents, and why
* three new problems campus customs could handle using the agents and tools we already built
* three new problems campus customs could not currently handle, and what new tools or agents would be needed to handle them

make the answers detailed and specific to campus customs, but keep the writing natural and straightforward like a student reflection. use the actual ticket results, agent behavior, tool usage, approvals, and cahs changes from our run as evidence.

Result:
- Replaced the "Coming later" Reflection tab in `output/desk_tickets.html` with a full first-person reflection (only that tab changed; the Expected, Actual, and Cash sections are untouched). It opens with a stats strip drawn from the Problem 9 audit trail: 5 runs, 65 model calls, 65 tool calls (16 were `get_ticket`, 15 `delegate_task`), 150,963 tokens, 3 approvals + 1 human decision, $3,400 → $152.
- Section 1 (performance): 101 "good" (caught the invoice #501 dependency, but it took 2 runs, `get_ticket(101)` was called 6×, there was a redundant `check_vendor_status`, and the customer draft leaked internal process). 102 "best" (10 calls, 27 s, Facilities delegated to Accounting itself; notes the Problem 5 "not overdue" prompt fix). 103 "mixed, but the right outcome" (correct needs_human, margin checks, and $264 PO refused against $152, but the most expensive run at 50,272 tokens, a double delegation to Accounting, a $0 probe call, and qty 20 instead of 8).
- Section 2 (expected vs actual): a table per ticket of what matched and what differed, plus the lesson that the plan got who and which tools right, but treated the tickets as independent when they share one cash account and one vendor.
- Section 3 (one agent vs many): 102 as the clearest single-agent case; almost half of all tool calls were hand-offs or re-reads, and only 5 changed money; thin Facilities and Customer Service agents; the cash-coordination machinery the multi-agent design forced (pending_total, proposals list, dedupe, validator); and what splitting did buy (tool scoping, a clear audit and dashboard).
- Section 4 (can handle now): Crest Mug restock via Elm City Gifts ($3.50 each, no open invoice); a Yale Cap discount (40 in stock, $6 cost / $22 list) via the decision flow; October rent (next_due 2026-10-02) correctly refused at $152.
- Section 5 (can't handle yet): recording the 8-hoodie sale ($417.60; needs a sales table and a `record_sale` tool, revenue not modeled); receiving the tee on 2026-09-05 (needs a purchase_orders table, `receive_shipment`, and date advance); inbound replies and new tickets (needs an inbox → `create_ticket` tool, human-approved sending, and a cash-forecast tool).
- Verification: every number was checked against `audit_trail.json`, `resolved_tickets.json`, and the DB. The HTML parser found no errors and no "Coming later" left (3 Expected + 3 Actual sections intact). Rendered in headless Chromium with no page errors.

---

# Problem 11: Prepare the submission folder

My prompt:
prepare my project files for submission based on the required file structure in the screenshot. check my current project against it and make sure all of the required files and folders are there and in the correct locations.

make sure the README includes the required instructions for resetting the database, starting the mcp server, starting the fastapi backend, and starting the react dashboard. also make sure .gitignore prevents my real .env and any api keys or secrets from being included, but keep both database files under data/.

don't push anything to github yet. just prepare and organize the files for submission and let me know if anything is missing or needs to be fixed.

Result:
- Checked the project against the required structure (hw5/ root, data/, mcp_server/, frontend/, backend/ with prompts/, output/). Missing: the root `README.md` (now created) and `output/github_url.txt` (still missing; it needs the GitHub repo URL, which doesn't exist yet because nothing has been pushed).
- Created `README.md`: overview and architecture, the shop rules, project layout, one-time setup (venv, pip, npm, .env), and step-by-step sections for **1. resetting the database** (cp command, `POST /api/reset`, dashboard Reset desk, CLI auto-reset), **2. starting the MCP server** (standalone stdio, plus Claude Code via `.mcp.json`), **3. starting the FastAPI backend** (`cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000`, route table), **4. starting the React dashboard** (`cd frontend && npm run dev`, how to use it), and a results summary.
- Rewrote `.gitignore`: ignores `.env`, `.env.*` (except `.env.example`), `frontend/.env*` (except the example), `*.pem`, `*.key`, `secrets*.json`, `credentials*.json`, `.venv/`, `__pycache__/`, `node_modules/`, `frontend/dist/`, temp files, and `.DS_Store`. It explicitly keeps `data/campus_customs.db` and `data/campus_customs_new.db`.
- Built a clean `hw-5/hw5/` submission folder by copying (rsync) and excluding `.venv`, `node_modules`, `__pycache__`, `.DS_Store`, `frontend/dist`, and any `.env`. Size 3.6 MB.

Verification:
- Secrets scan: no key patterns found in any project file, and the real PORTKEY_API_KEY value appears in no file. No `.env` exists in the project or in hw5/.
- `git check-ignore` test in a scratch repo: `.env`, `.env.local`, `frontend/.env`, `secret.key`, `.venv/`, and `node_modules/` are ignored. `.env.example`, `frontend/.env.example`, both databases, and README are included.
- Both databases were copied byte-identical. The original's checksum is unchanged (`f447ca6a…`).
- The copy runs from its own paths: imported backend.main/team from hw5/ and called `get_cash_balance` through the MCP server in hw5/ → $152.00. `.mcp.json` is valid.
- Frontend copy: `npm ci` + `npm run build` succeeded in a scratch folder, so no node_modules was added to hw5/.

Notes:
- Nothing was committed or pushed.
- hw5/ contains a few files not shown in the screenshot, which the code needs to run: `backend/agents/` (the five agent files), `backend/team.py`, `backend/audit.py`, `backend/run_tickets.py`, `backend/__init__.py`, and `output/board_state.json` (the board's approvals, results, and human decision).
