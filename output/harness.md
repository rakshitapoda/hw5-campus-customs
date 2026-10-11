# Campus Customs Multi-Agent Operations — Harness

**Contents:** Databases · Database tables · How the open tickets connect · MCP server tools · Agent team · Audit trail · Backend routes · Dashboard · Safety and guardrails · Full run results and output files

**System:** React dashboard (`frontend/`, :5173) → FastAPI backend (`backend/main.py`, :8000) → five PydanticAI agents (`gpt-6-luna` via Portkey) → campus-customs MCP server (`mcp_server/server.py`) → `data/campus_customs_new.db`.

## Databases

| File | Role |
|---|---|
| `data/campus_customs.db` | Original database. Read-only; never modified. |
| `data/campus_customs_new.db` | Working copy of the original. Agents and tools read from and write to this copy. Reset it from the original before each full ticket-resolution run. |

## Database tables

### `desk`
| Field | Type | Meaning |
|---|---|---|
| `date_today` | TEXT | The shop's "today" (currently `2026-08-31`). |
| `notes` | TEXT | Free-form shop notes (currently empty). |

**Why it matters:** `date_today` is the only valid source of the current date. Agents must use it, not the system clock, to decide whether rent or invoices are overdue and to calculate restock arrival dates.

### `tickets`
| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Ticket number. |
| `type` | TEXT | Kind of task (`customer_order`, `rent_notice`, `price_override`). |
| `requester` | TEXT | Who raised the ticket (customer, landlord, student org). |
| `subject` | TEXT | Short title. |
| `sku` | TEXT | Product involved, if any → `inventory.sku` / `pricing.sku`. |
| `size` | TEXT | Product size, if any → `inventory.size`. |
| `qty` | INTEGER | Quantity requested. |
| `lease_id` | INTEGER FK | Related lease → `leases.id`. |
| `invoice_id` | INTEGER FK | Related vendor invoice → `invoices.id`. |
| `status` | TEXT | Ticket state (`open` for all three today). |
| `notes` | TEXT | Request details in the requester's words. |
| `created_at` | TEXT | ISO timestamp of when the ticket was opened. |

**Why it matters:** This is the agents' work queue. The Boss Agent reads each open ticket and uses `type` and the linked fields to decide which agent handles it.

### `inventory`
| Field | Type | Meaning |
|---|---|---|
| `sku` | TEXT PK (with `size`) | Product code. |
| `name` | TEXT | Product name. |
| `size` | TEXT PK (with `sku`) | Size (`S`/`M`/`L`/`XL`, or `OS` = one size). |
| `qty` | INTEGER | Units on hand. |
| `location` | TEXT | Aisle where the product is shelved. |

**Why it matters:** The Inventory Agent checks stock by SKU **and** size here, and finds shortages (for example, `CC-TEE-WHITE` size S has 0 units, and `CC-HOOD-NAVY` size M has only 8).

### `pricing`
| Field | Type | Meaning |
|---|---|---|
| `sku` | TEXT PK | Product code → `inventory.sku`. |
| `unit_cost` | REAL | What the shop pays per unit. |
| `list_price` | REAL | Normal selling price per unit. |

**Why it matters:** The Accounting Agent uses cost and price to calculate margins. That tells it how much discount is possible on a price-override request without selling below cost, and what a restock order would cost.

### `vendors`
| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Vendor ID → referenced by `invoices.vendor_id`. |
| `name` | TEXT | Vendor name. |
| `specialty` | TEXT | What the vendor supplies (apparel reprint, mugs/small goods, courier). |
| `lead_days` | INTEGER | Days from order to delivery. |

**Why it matters:** The Inventory Agent uses `specialty` to pick the right restock vendor. Restock timing must come from `lead_days` in this table, never a guessed value.

### `leases`
| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Lease ID → referenced by `tickets.lease_id`. |
| `space_name` | TEXT | The rented space (Chapel Street shop). |
| `landlord` | TEXT | Who is paid the rent. |
| `monthly_rent` | REAL | Rent amount. |
| `next_due` | TEXT | Next rent due date. |
| `notes` | TEXT | Lease notes. |

**Why it matters:** The Facilities Agent uses this table to check a rent notice against the actual lease: correct landlord, amount, and due date compared with `desk.date_today`. It then has the rent payment prepared for human approval.

### `cash_accounts`
| Field | Type | Meaning |
|---|---|---|
| `name` | TEXT PK | Account name (`checking`). |
| `balance` | REAL | Current balance. |
| `date` | TEXT | Date the balance was last updated. |

**Why it matters:** The Accounting Agent checks that there is enough cash before proposing any payment. A payment must be refused if it would make the balance negative. Cash only ever decreases in this assignment.

### `payments`
| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Payment ID. |
| `kind` | TEXT | What was paid (e.g. invoice or rent). |
| `ref_id` | INTEGER | ID of the paid item (invoice or lease). |
| `amount` | REAL | Amount paid. |
| `account` | TEXT | Cash account it was paid from → `cash_accounts.name`. |
| `paid_at` | TEXT | Date the payment was made. |
| `approved_by` | TEXT | The human who approved it. |

**Why it matters:** This is the record of executed payments (currently empty). A row is written only after a human approves the payment, so `approved_by` is required. Paying also updates the related invoice or lease and the cash balance.

### `invoices`
| Field | Type | Meaning |
|---|---|---|
| `id` | INTEGER PK | Invoice ID → referenced by `tickets.invoice_id`. |
| `vendor_id` | INTEGER FK | Vendor owed → `vendors.id`. |
| `amount` | REAL | Amount owed. |
| `due_date` | TEXT | Payment due date. |
| `status` | TEXT | `open` (unpaid) or settled. |
| `description` | TEXT | What the invoice was for. |

**Why it matters:** A vendor with an open unpaid invoice will not ship new products. Before the Inventory Agent can restock from a vendor, the Accounting Agent must check here and get any open invoice paid (with approval). Comparing `due_date` with `desk.date_today` shows which invoices are overdue.

## How the open tickets connect to the database

| Ticket | Request | Linked data | What it means |
|---|---|---|---|
| **101** `customer_order` (Tauhid Zaman) | 1 × `CC-TEE-WHITE` size S | `inventory`: S qty = 0 · `invoices` 501 (via `invoice_id`) → `vendors` 1 Bulldog Print Co (apparel, 5 lead days) | Out of stock. The restock vendor is Bulldog Print Co, but invoice 501 ($840, due 2026-08-28) is still open and overdue, so they won't ship until it's paid with human approval. After that, a restock takes 5 days. Customer Service drafts an update for the customer. |
| **102** `rent_notice` (Elm City Properties) | Rent due in 2 days | `leases` 1: Chapel Street shop, $2,400, due 2026-09-02 | The notice matches the lease (2026-08-31 + 2 days = 2026-09-02). Facilities and Accounting prepare a $2,400 rent payment for human approval. |
| **103** `price_override` (Yale AI Club) | 20 × `CC-HOOD-NAVY` size M, bulk discount | `inventory`: M qty = 8 · `pricing`: cost $22, list $58 · apparel vendor = Bulldog Print Co | Only 8 of 20 in stock. A restock of 12 needs Bulldog Print Co, which is blocked by the same invoice 501. Any discount must keep the price above the $22 cost. |

**Cash constraint:** `checking` = $3,400. Invoice 501 ($840) + rent ($2,400) = $3,240, which would leave $160. Any further spending, such as a hoodie restock purchase order, must fit within whatever cash remains.

## MCP server tools

Server: `mcp_server/server.py` (FastMCP, stdio). It's registered for Claude Code in `.mcp.json` as `campus-customs`, and the agents launch the same script through PydanticAI's `MCPToolset`. Every tool works on `data/campus_customs_new.db` only and uses `desk.date_today` as today. The agents get only read tools and the two `prepare_*` tools, which validate and return a proposal for human approval and **never write**. The four backend-only tools at the bottom of the table (`list_tickets`, `update_ticket_status`, `execute_payment`, `execute_purchase_order`) are not given to any agent. The money tools are called only by the FastAPI approve route after a named human approves. The MCP tools are the only access to shop data for both the agents and the backend.

| Tool | Inputs | Returns | Tables used | Agents |
|---|---|---|---|---|
| `get_shop_date` | — | `date_today`, `notes` | `desk` | all five |
| `list_open_tickets` | — | Every ticket with `status = 'open'` | `tickets` | boss |
| `get_ticket` | `ticket_id` | All fields of one ticket | `tickets` | all five |
| `check_inventory` | `sku`, `size` | Name, qty, location, `in_stock`, `unit_cost`, `list_price` | `inventory`, `pricing` | inventory, customer_service |
| `check_vendor_status` | `vendor_id` (optional) | Specialty, `lead_days`, open invoices with `days_overdue`, `open_balance`, `can_ship` | `vendors`, `invoices`, `desk` | inventory, accounting |
| `get_lease` | `lease_id` | Lease row plus `days_until_due`, `is_overdue` | `leases`, `desk` | facilities |
| `get_invoice` | `invoice_id` | Invoice plus vendor name/lead time, `days_overdue`, `is_overdue` | `invoices`, `vendors`, `desk` | accounting |
| `get_cash_balance` | `account` (optional) | Balance and date per account | `cash_accounts` | accounting |
| `check_margin` | `sku`, `proposed_unit_price`, `qty` | Discount % vs. list, unit/total margin, margin %, `below_cost` | `pricing` | accounting |
| `prepare_payment` | `kind` (`invoice`/`rent`), `ref_id`, `account`, `pending_total` | Proposal: payee and amount **from the DB**, cash before/after, status `awaiting_human_approval` or `refused` (cash would go negative). Nothing is written. | `invoices`, `vendors`, `leases`, `cash_accounts`, `desk` | accounting |
| `prepare_purchase_order` | `vendor_id`, `sku`, `size`, `qty`, `account`, `pending_total` | Proposal: cost = `unit_cost × qty`, arrival = `date_today + lead_days`, status `blocked` (vendor has an open invoice), `refused` (not enough cash), or `awaiting_human_approval`. Nothing is written. | `vendors`, `invoices`, `inventory`, `pricing`, `cash_accounts`, `desk` | accounting |
| `list_tickets` | — | Every ticket (open and resolved) | `tickets` | backend only |
| `update_ticket_status` | `ticket_id`, `status` (`open`/`resolved`) | **Writes** `tickets.status` | `tickets` | backend only |
| `execute_payment` | `kind`, `ref_id`, `approved_by`, `account` | **Writes, after human approval.** In one transaction: refuses if `approved_by` is empty, the invoice isn't open, or cash would go negative. Otherwise inserts a `payments` row (`paid_at = desk.date_today`, `approved_by`), sets the invoice to `paid` (or moves the lease's `next_due` forward one month for rent), and debits `cash_accounts`. | `payments`, `invoices`, `vendors`, `leases`, `cash_accounts`, `desk` | backend only (approve route) |
| `execute_purchase_order` | `vendor_id`, `sku`, `size`, `qty`, `approved_by`, `account` | **Writes, after human approval.** Refuses while the vendor has an open invoice or if cash would go negative. Otherwise inserts a `payments` row (`kind = 'purchase_order'`, `ref_id` = vendor id) and debits cash. Stock is unchanged until delivery (`lead_days`). | `payments`, `vendors`, `invoices`, `inventory`, `pricing`, `cash_accounts`, `desk` | backend only (approve route) |

`payments` rows are written only by `execute_payment` / `execute_purchase_order`, so every row has a human `approved_by`.

Unknown SKUs, sizes, tickets, leases, invoices, vendors, or accounts return an error saying the record doesn't exist. The tools never substitute or invent data.

## Agent team

Code: `backend/team.py` (shared setup), `backend/agents/<agent>.py` (one per agent), prompts in `backend/prompts/<agent>.md`, data types in `backend/models.py`. Entry point: `python -m backend.run_tickets` (full run) or `--ticket N`.

- **Model:** every agent builds its own `OpenAIResponsesModel("gpt-6-luna")` through Portkey (`PORTKEY_API_KEY`, `https://api.portkey.ai/v1`). No other model and no fallback. The Responses API is used because this Portkey route rejects function tools on chat completions while reasoning is enabled.
- **Delegation (full connectivity):** every agent has the `delegate_task(to_agent, task)` tool and may call any of the other four. The delegated agent runs with the same ticket budget and returns its `AgentReport` as JSON.
- **MCP access:** one shared `MCPToolset` connection. Each agent gets a filtered subset of tools (see the Agents column above).

| Agent | Role | Output type |
|---|---|---|
| **boss** | Reads the ticket, routes it, delegates, and makes the final decision. Starts every ticket. | `TicketResolution` (decision, `recommended_status`, payment/PO requests, message drafts, open issues) |
| **inventory** | Stock by SKU **and** size, shortages, which vendor can restock (specialty + `lead_days`), and whether the vendor is blocked by an open invoice. | `AgentReport` |
| **accounting** | Cash, invoices, margins. Prepares payments and purchase orders for human approval. The only agent with the `prepare_*` tools. | `AgentReport` |
| **facilities** | Leases and rent. Verifies rent notices against the lease on record, then asks accounting to prepare the payment. | `AgentReport` |
| **customer_service** | Drafts customer-facing messages using only confirmed facts. Never sends them. | `AgentReport` |

## Audit trail

`output/audit_trail.json` is a JSON array that is **only appended to**. Each event is added by reading the file, appending, and replacing the file atomically, so earlier events are never removed. Every event has `timestamp`, `event`, `run_id`, and (for agent events) `ticket_id`, `agent`, `depth`, and `chain` (the delegation path, e.g. `["boss", "facilities", "accounting"]`).

| Event | Recorded when / contents |
|---|---|
| `run_start` / `tickets_selected` / `run_end` | Start of a run (model, whether the DB was reset), which tickets it covers, and the end |
| `agent_start` | An agent begins: the prompt or delegated task it received |
| `model_request` | Each loop step's input to the model: tool results returned (tool, call id, result) and retry messages |
| `model_response` | Each model reply: model name, text, tool calls with arguments, and token usage |
| `delegation` / `delegation_refused` | One agent hands work to another (task text), or a delegation is blocked and why |
| `agent_end` | The agent's validated final output and cumulative usage for the ticket |
| `agent_error` / `ticket_timeout` / `run_aborted` | Failures (error message), time-limit hits, and manually stopped runs |
| `payment_approved` / `approval_refused` | A human approval through the API (approver, `execute_*` result, whether the ticket resolved), or an approval the execute tool refused (and why) |
| `db_reset` | The working DB was reset through the API |
| `human_decision` | A person recorded a decision on a ticket (who, what) |

Long strings are clipped at 2,000 characters.

## Backend routes

`backend/main.py` (FastAPI). Run from `backend/` with `uvicorn main:app --reload --port 8000`, then open http://localhost:8000/docs for interactive docs. On startup the app opens one MCP server connection and uses it for every route and agent run. Board state that isn't in the shop database is kept in `output/board_state.json`: approval items prepared by the agents, each ticket's latest agent result (decision and message drafts), and human decisions on judgment calls.

| Method | URL | What it does |
|---|---|---|
| GET | `/api/tickets` | All tickets with `status` (`open`/`resolved`), the latest agent result (decision, recommended status, message drafts), approval counts, and whether a run is in progress. |
| POST | `/api/tickets/{ticket_id}/run` | Starts the agent team (Boss first) on one ticket in the background and returns `202` with a `run_id`. `404` for an unknown ticket, `409` if it's already resolved or another run is in progress. Payments/POs the agents prepare become approval items. |
| POST | `/api/tickets/{ticket_id}/decision` | Body `{"decided_by": "<name>", "decision": "<text>"}`. Records a human answer to a judgment call the agents flagged as `needs_human` (e.g. which discount to grant, how much of an order to fill). The decision is added to the Boss's prompt on the next run as authoritative. **Never moves money.** `409` if the ticket is resolved. |
| GET | `/api/runs/{run_id}` | Run status: `running`, `completed` (with the Boss's `TicketResolution`), or `failed` (with the error). |
| GET | `/api/activity?limit=50&ticket_id=&run_id=` | Recent agent activity from `output/audit_trail.json`, newest first: agent, what it said (text, decision, or summary), tools called with arguments, delegations, approvals, and resets. |
| GET | `/api/approvals?status=&ticket_id=` | Payments and purchase orders the agents prepared, with status `pending`, `blocked`, `refused`, or `approved`. |
| POST | `/api/approvals/{approval_id}/approve` | Body `{"approved_by": "<name>"}`. **The only route that moves money.** Approves a `pending` item and runs `execute_payment` / `execute_purchase_order`, which writes the `payments` row, updates the invoice or lease, and debits cash. `409` if the item isn't pending or the tool refuses (insufficient cash, vendor blocked, invoice already paid). `422` if `approved_by` is empty. Marks the ticket `resolved` when the agents said it only needed approvals and all of them are now approved. |
| GET | `/api/cash` | Current `checking` balance from `cash_accounts`. |
| POST | `/api/reset` | Copies `data/campus_customs.db` over `data/campus_customs_new.db` and clears the board state. The audit trail is kept, because it's append-only. `409` while a run is in progress. |

## Dashboard

`frontend/` (React 19 + Vite + TypeScript). Run with `npm run dev`, then open http://localhost:5173. It talks only to the backend routes above. The backend's CORS allows `localhost:5173` and any other localhost port. Full design rationale: `output/design.md`.

| Area | What it shows / does | Routes used |
|---|---|---|
| Top bar | Books date (`cash_accounts.date`), "N awaiting sign-off", backend connection, **Reset desk** | `/api/cash`, `/api/reset` |
| Ticket queue (left) | The three tickets as stubs with status colors, the agents who worked each one, a "to sign" badge, and a **RESOLVED** stamp | `/api/tickets` (polled every 5 s) |
| Ticket header | Subject, the requester's note, status, **Start agent team** (disabled while resolved or while another run is going) | `POST /api/tickets/{id}/run` |
| Agent floor | Five stations, each with its own color and icon. Live phase (working / waiting / done / not on this ticket), speech bubble, and tools used | `/api/activity?run_id=` (every 1.5 s while running), `/api/runs/{id}` |
| Boss's decision | Final decision, open issues, drafted messages ("Draft · not sent"), and a green resolved note naming the approvers | `/api/tickets` |
| Your decision | Shown for `needs_human` tickets: a person records the judgment call, which the next run carries out | `POST /api/tickets/{id}/decision` |
| Live feed / What each agent did | Step-by-step log with tool arguments, and a per-agent summary with hand-offs and tool counts | `/api/activity` |
| Checking (right) | Balance from `cash_accounts`, a delta flash after approvals, a cash bar, and paid / awaiting / left-if-approved figures | `/api/cash`, `/api/approvals` |
| Sign-off tray (right) | Pending payment slips with "checking after". **Approve** opens a confirm dialog and requires a name. Blocked/refused items show the reason with no button. Approved items list the approver | `/api/approvals`, `POST /api/approvals/{id}/approve` |

## Safety and guardrails

**Money**
- Agents can't move money. Their only money tools (`prepare_payment`, `prepare_purchase_order`) return proposals with `requires_human_approval: true` and write nothing. The `execute_*` tools are not in any agent's tool set.
- Money moves only through `POST /api/approvals/{id}/approve`. The route requires a non-empty `approved_by`, only accepts items the agents prepared that are still `pending` (not `blocked`, `refused`, or already `approved`), and the `execute_*` tool re-checks cash, invoice status, and vendor blocks live before writing. Each item can be approved once, and an invoice can't be paid twice.
- Payment amounts and payees come from the database (invoice amount, lease rent), never from what the model or an email says.
- Cash may never go negative: the prepare tools return `refused` when `balance − pending_total − amount < 0`. The runner shares the list of prepared items across all tickets in a run, and each agent is shown the running `pending_total`, so the cash check covers everything that might be approved together.
- A vendor with an open invoice won't ship: `prepare_purchase_order` returns `blocked` while `invoices.status = 'open'` for that vendor.
- **Output validation:** an agent's final output is rejected (and the model is told to retry) if any payment or purchase order in it doesn't exactly match a `prepare_*` tool result from this run (same kind/ref_id/amount/status, or vendor/SKU/size/qty/cost/status).
- Re-preparing the same item replaces the earlier entry instead of creating a duplicate. Agents are told which items already exist.
- Only the accounting agent has the `prepare_*` tools.

**Customers and vendors**
- No email or contact tools exist. Customer, landlord, and vendor messages are `MessageDraft`s for a human to review.
- The customer-service prompt forbids promising dates or discounts that aren't confirmed or approved, and forbids mentioning internal matters (unpaid invoices, cash, margins).
- Discounts are never granted by an agent. Accounting reports margins (`below_cost` must be false), and the ticket is marked `needs_human` until a person records a decision through `POST /api/tickets/{id}/decision`. The Boss carries out that decision only within the shop rules.

**Data integrity**
- Shop data comes only through the MCP tools, and each agent has only the tools its role needs.
- Today is `desk.date_today`. Lead times come from `vendors.lead_days`.
- `data/campus_customs.db` is never opened by the server. A full CLI run, or `POST /api/reset`, copies it over `data/campus_customs_new.db` (rule 8). The API refuses to reset or start a second run while an agent run is in progress.

**Token / loop limits** (constants in `backend/team.py` and `backend/run_tickets.py`, shared by all agents on a ticket via one `RunUsage`)

| Limit | Value |
|---|---|
| Model requests per ticket | 40 |
| Tool calls per ticket | 60 |
| Total tokens per ticket | 250,000 |
| Output tokens per model response (includes reasoning) | 4,000 |
| Delegation depth (boss → agent → agent → agent) | 3 |
| Delegations per ticket | 8 |
| Agents can't delegate to themselves or to an agent already in the current chain | prevents A→B→A loops |
| Retries per tool / output validation | 2 |
| Model HTTP timeout / retries | 120 s / 1 |
| Wall-clock limit per ticket | 600 s |
| Portkey cache | forced refresh, so old replies are never replayed |

When any limit is hit, the run for that ticket stops, the error is written to the audit trail, and the runner moves on to the next ticket.

## Full run results and output files

Full run (Problem 9): the working DB was reset through `POST /api/reset`, then the tickets were run through the API in order 101 → 102 → 103. Every payment was approved through `POST /api/approvals/{id}/approve` (approver: Rakshita Podagatlapalli).

| Step | Cash |
|---|---|
| Start (after reset) | $3,400.00 |
| #101 invoice #501 → Bulldog Print Co (payment #1) | −$840.00 → $2,560.00 |
| #101 restock 1 × CC-TEE-WHITE S (payment #2, arrives 2026-09-05) | −$8.00 → $2,552.00 |
| #102 rent, lease #1 → Elm City Properties (payment #3; next_due → 2026-10-02) | −$2,400.00 → $152.00 |
| #103 human decision: 10% off ($52.20) on the 8 in stock, no restock; 12-unit PO ($264.00) refused for insufficient cash | $0.00 → **$152.00** |

Ending balance **$152.00** = `cash_accounts.checking`. Tickets 101 and 103 each needed two runs: 101 because the PO could only be prepared after the invoice was paid, and 103 because the discount needed a human decision.

| File | Contents |
|---|---|
| `output/harness.md` | This document |
| `output/mcp_smoke.json` | MCP tool smoke tests with DB verification (Problem 4) |
| `output/audit_trail.json` | Append-only log of every agent step, delegation, approval, decision, and reset |
| `output/board_state.json` | Backend board state (approvals, latest results, human decisions) |
| `output/desk_tickets.html` | Expected plan vs. actual run per ticket, plus the Cash tab |
| `output/resolved_tickets.json` | Per ticket: final status, outcome, agent contributions, human approvals and decisions, cash change |
| `output/resolved_board.html` | Dashboard screenshots of resolved tickets 101, 102, and 103 |
| `output/design.md` | Dashboard design rationale |

