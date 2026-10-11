# Campus Customs MCP server

A FastMCP server (`server.py`, stdio transport) that gives the Campus Customs agents access to the shop database. It works on the working copy `data/campus_customs_new.db` only. The original `data/campus_customs.db` is never opened. "Today" is always `desk.date_today`.

The agents get only the read tools and the `prepare_*` tools, which validate and return a proposal for a human to approve and never write. The four **backend-only** tools at the end of the table write to the database. No agent is given them, and the money tools are called only by the FastAPI approve route after a named human approves.

## Tools

| Tool | Arguments | What it returns | Tables |
|---|---|---|---|
| `get_shop_date` | — | The shop's `date_today` and desk notes | `desk` |
| `list_open_tickets` | — | All tickets with status `open` | `tickets` |
| `get_ticket` | `ticket_id` | One ticket with all fields | `tickets` |
| `check_inventory` | `sku`, `size` | Stock on hand, location, `in_stock`, unit cost, list price | `inventory`, `pricing` |
| `check_vendor_status` | `vendor_id` (optional) | Specialty, lead days, open invoices, `can_ship` | `vendors`, `invoices`, `desk` |
| `get_lease` | `lease_id` | Lease details, `days_until_due`, `is_overdue` | `leases`, `desk` |
| `get_invoice` | `invoice_id` | Invoice with vendor name, lead days, `days_overdue` | `invoices`, `vendors`, `desk` |
| `get_cash_balance` | `account` (optional) | Cash account balances | `cash_accounts` |
| `check_margin` | `sku`, `proposed_unit_price`, `qty` | Discount %, unit/total margin, `below_cost` | `pricing` |
| `prepare_payment` | `kind` (`invoice` or `rent`), `ref_id`, `account`, `pending_total` | Payment proposal (amount and payee from the DB), cash check, status `awaiting_human_approval` or `refused` | `invoices`, `vendors`, `leases`, `cash_accounts`, `desk` |
| `prepare_purchase_order` | `vendor_id`, `sku`, `size`, `qty`, `account`, `pending_total` | Restock proposal: cost, expected arrival, status `awaiting_human_approval`, `blocked` (vendor has an open invoice), or `refused` (not enough cash) | `vendors`, `invoices`, `inventory`, `pricing`, `cash_accounts`, `desk` |
| `list_tickets` *(backend)* | — | All tickets, open and resolved | `tickets` |
| `update_ticket_status` *(backend)* | `ticket_id`, `status` | Sets a ticket to `open` or `resolved` | `tickets` |
| `execute_payment` *(backend, after human approval)* | `kind`, `ref_id`, `approved_by`, `account` | Pays an open invoice (marks it `paid`) or one month's rent (moves `next_due` forward), inserts a `payments` row, and debits cash. Refused without an approver, for an invoice that isn't open, or if cash would go negative. | `payments`, `invoices`, `vendors`, `leases`, `cash_accounts`, `desk` |
| `execute_purchase_order` *(backend, after human approval)* | `vendor_id`, `sku`, `size`, `qty`, `approved_by`, `account` | Pays for a restock order and inserts a `payments` row (`kind = 'purchase_order'`). Refused while the vendor has an open invoice or if cash would go negative. | `payments`, `vendors`, `invoices`, `inventory`, `pricing`, `cash_accounts`, `desk` |

Unknown IDs, SKUs, sizes, or accounts return an error instead of made-up data.

## Running

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp data/campus_customs.db data/campus_customs_new.db   # first time only
.venv/bin/python mcp_server/server.py                  # stdio server
```

Claude Code picks it up from `.mcp.json` at the project root (server name `campus-customs`). The agent team and the FastAPI backend in `backend/` launch the same script through PydanticAI's `MCPToolset`.
