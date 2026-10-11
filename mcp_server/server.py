"""Campus Customs MCP server.

Exposes the shop database to the agents and the backend. Every tool works on the
working copy data/campus_customs_new.db; the original data/campus_customs.db is never opened.
Dates are measured against desk.date_today, not the computer's clock.

The agents only get read tools and the prepare_* tools (which never write). The
write tools at the bottom (update_ticket_status, execute_payment,
execute_purchase_order) are called only by the FastAPI backend, and the money
tools only after a human approves the item.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "campus_customs_new.db"

mcp = FastMCP(
    "campus-customs",
    instructions=(
        "Tools for the Campus Customs shop database. All answers come from "
        "data/campus_customs_new.db; today's date is desk.date_today."
    ),
)


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise ToolError(
            f"Working database not found at {DB_PATH}. "
            "Copy data/campus_customs.db to data/campus_customs_new.db first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def shop_today(conn: sqlite3.Connection) -> date:
    row = conn.execute("SELECT date_today FROM desk").fetchone()
    if row is None:
        raise ToolError("desk table has no date_today row.")
    return date.fromisoformat(row["date_today"])


@mcp.tool
def check_inventory(sku: str, size: str) -> dict:
    """Look up stock on hand for one product SKU and size, with its unit cost and list price.

    Use for customer orders and bulk/discount requests to see whether the
    requested quantity is available and what the margin is.
    """
    with closing(connect()) as conn:
        item = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        ).fetchone()
        if item is None:
            sizes = [r["size"] for r in conn.execute("SELECT size FROM inventory WHERE sku = ?", (sku,))]
            if not sizes:
                raise ToolError(f"SKU {sku!r} is not in inventory.")
            raise ToolError(f"SKU {sku!r} has no size {size!r}. Sizes on record: {', '.join(sizes)}.")
        price = conn.execute(
            "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()

    return {
        **dict(item),
        "in_stock": item["qty"] > 0,
        "unit_cost": price["unit_cost"] if price else None,
        "list_price": price["list_price"] if price else None,
    }


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Look up a shop lease: space, landlord, monthly rent, and next due date.

    Also reports days until rent is due (negative = overdue), measured from
    desk.date_today. Use to verify rent notices against the actual lease.
    """
    with closing(connect()) as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            raise ToolError(f"Lease {lease_id} does not exist.")
        today = shop_today(conn)

    days_until_due = (date.fromisoformat(lease["next_due"]) - today).days
    return {
        **dict(lease),
        "date_today": today.isoformat(),
        "days_until_due": days_until_due,
        "is_overdue": days_until_due < 0,
    }


@mcp.tool
def check_vendor_status(vendor_id: int | None = None) -> list[dict]:
    """List vendors with their specialty, lead time, and any open (unpaid) invoices.

    A vendor will not ship new products while it has an open invoice, so
    can_ship is False whenever open_invoices is non-empty. Overdue status is
    measured from desk.date_today. Omit vendor_id to list every vendor.
    """
    with closing(connect()) as conn:
        if vendor_id is None:
            vendors = conn.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id").fetchall()
        else:
            vendors = conn.execute(
                "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
            ).fetchall()
            if not vendors:
                raise ToolError(f"Vendor {vendor_id} does not exist.")
        today = shop_today(conn)

        results = []
        for vendor in vendors:
            invoices = conn.execute(
                "SELECT id, amount, due_date, status, description FROM invoices "
                "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
                (vendor["id"],),
            ).fetchall()
            open_invoices = []
            for inv in invoices:
                days_overdue = (today - date.fromisoformat(inv["due_date"])).days
                open_invoices.append({**dict(inv), "days_overdue": max(days_overdue, 0), "is_overdue": days_overdue > 0})
            results.append({
                **dict(vendor),
                "date_today": today.isoformat(),
                "open_invoices": open_invoices,
                "open_balance": sum(inv["amount"] for inv in open_invoices),
                "can_ship": not open_invoices,
            })
    return results


@mcp.tool
def get_shop_date() -> dict:
    """Return the shop's official date (desk.date_today) and desk notes.

    Always use this date, never the computer clock, for due dates and deliveries.
    """
    with closing(connect()) as conn:
        row = conn.execute("SELECT date_today, notes FROM desk").fetchone()
    if row is None:
        raise ToolError("desk table has no date_today row.")
    return dict(row)


@mcp.tool
def list_open_tickets() -> list[dict]:
    """List every ticket whose status is 'open', oldest first."""
    with closing(connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status = 'open' ORDER BY created_at, id"
        ).fetchall()
    return [dict(r) for r in rows]


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Return one ticket with all of its fields (type, requester, sku/size/qty, linked lease or invoice, notes)."""
    with closing(connect()) as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise ToolError(f"Ticket {ticket_id} does not exist.")
    return dict(row)


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Return one vendor invoice with the vendor's name and lead time, and whether it is overdue as of desk.date_today."""
    with closing(connect()) as conn:
        row = conn.execute(
            "SELECT i.id, i.vendor_id, v.name AS vendor_name, v.lead_days, i.amount, "
            "i.due_date, i.status, i.description "
            "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        if row is None:
            raise ToolError(f"Invoice {invoice_id} does not exist.")
        today = shop_today(conn)

    days_overdue = (today - date.fromisoformat(row["due_date"])).days
    return {
        **dict(row),
        "date_today": today.isoformat(),
        "days_overdue": max(days_overdue, 0),
        "is_overdue": row["status"] == "open" and days_overdue > 0,
    }


@mcp.tool
def get_cash_balance(account: str | None = None) -> list[dict]:
    """Return cash account balances. Omit account to list every account."""
    with closing(connect()) as conn:
        if account is None:
            rows = conn.execute("SELECT name, balance, date FROM cash_accounts ORDER BY name").fetchall()
        else:
            rows = conn.execute(
                "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,)
            ).fetchall()
            if not rows:
                raise ToolError(f"Cash account {account!r} does not exist.")
    return [dict(r) for r in rows]


@mcp.tool
def check_margin(sku: str, proposed_unit_price: float, qty: int = 1) -> dict:
    """Calculate the margin for selling qty units of a SKU at a proposed unit price.

    Uses pricing.unit_cost and pricing.list_price. Reports the discount versus
    list price and flags any price at or below cost.
    """
    if qty <= 0:
        raise ToolError("qty must be positive.")
    with closing(connect()) as conn:
        price = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()
    if price is None:
        raise ToolError(f"SKU {sku!r} has no pricing record.")

    unit_margin = proposed_unit_price - price["unit_cost"]
    return {
        **dict(price),
        "qty": qty,
        "proposed_unit_price": proposed_unit_price,
        "discount_pct": round((1 - proposed_unit_price / price["list_price"]) * 100, 2),
        "unit_margin": round(unit_margin, 2),
        "margin_pct": round(unit_margin / proposed_unit_price * 100, 2) if proposed_unit_price > 0 else None,
        "total_revenue": round(proposed_unit_price * qty, 2),
        "total_margin": round(unit_margin * qty, 2),
        "below_cost": unit_margin <= 0,
    }


def cash_check(conn: sqlite3.Connection, account: str, amount: float, pending_total: float) -> dict:
    row = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    if row is None:
        raise ToolError(f"Cash account {account!r} does not exist.")
    balance_after = row["balance"] - pending_total - amount
    return {
        "account": account,
        "cash_balance": row["balance"],
        "pending_total": pending_total,
        "balance_after": round(balance_after, 2),
        "sufficient_cash": balance_after >= 0,
    }


@mcp.tool
def prepare_payment(kind: str, ref_id: int, account: str = "checking", pending_total: float = 0.0) -> dict:
    """Prepare (but never execute) a payment for human approval.

    kind is 'invoice' (ref_id = invoices.id) or 'rent' (ref_id = leases.id).
    The amount and payee always come from the database. pending_total is the sum
    of other payments already proposed this run; cash must cover all of them.
    Returns status 'awaiting_human_approval', or 'refused' with a reason.
    Nothing is written to the database.
    """
    with closing(connect()) as conn:
        today = shop_today(conn)
        if kind == "invoice":
            row = conn.execute(
                "SELECT i.amount, i.due_date, i.status, i.description, v.name AS payee "
                "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ref_id,),
            ).fetchone()
            if row is None:
                raise ToolError(f"Invoice {ref_id} does not exist.")
            if row["status"] != "open":
                raise ToolError(f"Invoice {ref_id} has status {row['status']!r}; only open invoices can be paid.")
            due, description = row["due_date"], row["description"]
        elif kind == "rent":
            row = conn.execute(
                "SELECT monthly_rent AS amount, next_due, space_name, landlord AS payee FROM leases WHERE id = ?",
                (ref_id,),
            ).fetchone()
            if row is None:
                raise ToolError(f"Lease {ref_id} does not exist.")
            due, description = row["next_due"], f"Rent for {row['space_name']}"
        else:
            raise ToolError("kind must be 'invoice' or 'rent'.")
        cash = cash_check(conn, account, row["amount"], pending_total)

    refused = not cash["sufficient_cash"]
    return {
        "status": "refused" if refused else "awaiting_human_approval",
        "reason": "Insufficient cash: balance would go negative." if refused else None,
        "requires_human_approval": True,
        "kind": kind,
        "ref_id": ref_id,
        "payee": row["payee"],
        "amount": row["amount"],
        "due_date": due,
        "description": description,
        "date_today": today.isoformat(),
        **cash,
    }


@mcp.tool
def prepare_purchase_order(
    vendor_id: int, sku: str, size: str, qty: int, account: str = "checking", pending_total: float = 0.0
) -> dict:
    """Prepare (but never place) a restock purchase order for human approval.

    Cost comes from pricing.unit_cost and the expected arrival from
    desk.date_today + vendors.lead_days. Status is 'blocked' while the vendor has
    an open invoice (vendors won't ship until it is paid), 'refused' if cash
    would go negative (including pending_total), otherwise 'awaiting_human_approval'.
    Nothing is written to the database.
    """
    if qty <= 0:
        raise ToolError("qty must be positive.")
    with closing(connect()) as conn:
        today = shop_today(conn)
        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        if vendor is None:
            raise ToolError(f"Vendor {vendor_id} does not exist.")
        item = conn.execute(
            "SELECT name, qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        if item is None:
            raise ToolError(f"SKU {sku!r} size {size!r} is not in inventory.")
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            raise ToolError(f"SKU {sku!r} has no pricing record.")
        open_invoices = [
            r["id"] for r in conn.execute(
                "SELECT id FROM invoices WHERE vendor_id = ? AND status = 'open'", (vendor_id,)
            )
        ]
        total_cost = round(price["unit_cost"] * qty, 2)
        cash = cash_check(conn, account, total_cost, pending_total)

    if open_invoices:
        status, reason = "blocked", f"Vendor has open unpaid invoice(s) {open_invoices}; it will not ship until paid."
    elif not cash["sufficient_cash"]:
        status, reason = "refused", "Insufficient cash: balance would go negative."
    else:
        status, reason = "awaiting_human_approval", None
    return {
        "status": status,
        "reason": reason,
        "requires_human_approval": True,
        "vendor_id": vendor["id"],
        "vendor_name": vendor["name"],
        "vendor_specialty": vendor["specialty"],
        "sku": sku,
        "name": item["name"],
        "size": size,
        "qty": qty,
        "on_hand": item["qty"],
        "unit_cost": price["unit_cost"],
        "total_cost": total_cost,
        "lead_days": vendor["lead_days"],
        "date_today": today.isoformat(),
        "expected_arrival_if_ordered_today": (today + timedelta(days=vendor["lead_days"])).isoformat(),
        "open_invoice_ids": open_invoices,
        **cash,
    }


@mcp.tool
def list_tickets() -> list[dict]:
    """List every ticket (open and resolved) with its status, oldest first."""
    with closing(connect()) as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY created_at, id").fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Write tools: backend only. No agent is given these tools.
# ---------------------------------------------------------------------------

TICKET_STATUSES = ("open", "resolved")


@mcp.tool
def update_ticket_status(ticket_id: int, status: str) -> dict:
    """Set a ticket's status to 'open' or 'resolved'. Backend only."""
    if status not in TICKET_STATUSES:
        raise ToolError(f"status must be one of {TICKET_STATUSES}.")
    with closing(connect()) as conn, conn:
        cur = conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        if cur.rowcount == 0:
            raise ToolError(f"Ticket {ticket_id} does not exist.")
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return dict(row)


def add_one_month(day: date) -> date:
    year, month = (day.year + 1, 1) if day.month == 12 else (day.year, day.month + 1)
    for d in (day.day, 30, 29, 28):  # clamp e.g. Jan 31 -> Feb 28
        try:
            return date(year, month, d)
        except ValueError:
            continue
    raise ValueError(day)


def require_approver(approved_by: str) -> str:
    approved_by = approved_by.strip()
    if not approved_by:
        raise ToolError("approved_by is required: every payment needs a named human approver.")
    return approved_by


def debit_cash(conn: sqlite3.Connection, account: str, amount: float, today: date) -> tuple[float, float]:
    """Subtract amount from an account, refusing if the balance would go negative."""
    row = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    if row is None:
        raise ToolError(f"Cash account {account!r} does not exist.")
    before = row["balance"]
    after = round(before - amount, 2)
    if after < 0:
        raise ToolError(f"Refused: insufficient cash in {account} (balance ${before:.2f}, payment ${amount:.2f}).")
    conn.execute(
        "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?", (after, today.isoformat(), account)
    )
    return before, after


def record_payment(conn, kind: str, ref_id: int, amount: float, account: str, today: date, approved_by: str) -> int:
    cur = conn.execute(
        "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
        (kind, ref_id, amount, account, today.isoformat(), approved_by),
    )
    return cur.lastrowid


@mcp.tool
def execute_payment(kind: str, ref_id: int, approved_by: str, account: str = "checking") -> dict:
    """Execute a human-approved payment. Backend only, after explicit human approval.

    kind 'invoice': pays invoices.id = ref_id in full and marks it 'paid'.
    kind 'rent': pays leases.id = ref_id one month's rent and moves next_due forward one month.
    In one transaction: inserts a payments row (paid_at = desk.date_today,
    approved_by = the human), updates the invoice/lease, and debits the cash
    account. Refused if cash would go negative or the invoice is not open.
    """
    approved_by = require_approver(approved_by)
    with closing(connect()) as conn, conn:
        today = shop_today(conn)
        if kind == "invoice":
            inv = conn.execute(
                "SELECT i.amount, i.status, v.name AS payee FROM invoices i "
                "JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ref_id,),
            ).fetchone()
            if inv is None:
                raise ToolError(f"Invoice {ref_id} does not exist.")
            if inv["status"] != "open":
                raise ToolError(f"Invoice {ref_id} has status {inv['status']!r}; it cannot be paid again.")
            amount, payee = inv["amount"], inv["payee"]
            before, after = debit_cash(conn, account, amount, today)
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
            updated = {"invoice_id": ref_id, "invoice_status": "paid"}
        elif kind == "rent":
            lease = conn.execute(
                "SELECT monthly_rent, next_due, landlord FROM leases WHERE id = ?", (ref_id,)
            ).fetchone()
            if lease is None:
                raise ToolError(f"Lease {ref_id} does not exist.")
            amount, payee = lease["monthly_rent"], lease["landlord"]
            before, after = debit_cash(conn, account, amount, today)
            next_due = add_one_month(date.fromisoformat(lease["next_due"])).isoformat()
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (next_due, ref_id))
            updated = {"lease_id": ref_id, "paid_due_date": lease["next_due"], "next_due": next_due}
        else:
            raise ToolError("kind must be 'invoice' or 'rent'.")
        payment_id = record_payment(conn, kind, ref_id, amount, account, today, approved_by)

    return {
        "status": "paid",
        "payment_id": payment_id,
        "kind": kind,
        "ref_id": ref_id,
        "payee": payee,
        "amount": amount,
        "account": account,
        "paid_at": today.isoformat(),
        "approved_by": approved_by,
        "balance_before": before,
        "balance_after": after,
        **updated,
    }


@mcp.tool
def execute_purchase_order(
    vendor_id: int, sku: str, size: str, qty: int, approved_by: str, account: str = "checking"
) -> dict:
    """Place and pay for a human-approved restock order. Backend only, after explicit human approval.

    Refused while the vendor has an open invoice (it won't ship) or if cash would
    go negative. Records a payments row (kind 'purchase_order', ref_id = vendor id)
    and debits cash. Stock is not changed: the goods arrive after vendors.lead_days.
    """
    approved_by = require_approver(approved_by)
    if qty <= 0:
        raise ToolError("qty must be positive.")
    with closing(connect()) as conn, conn:
        today = shop_today(conn)
        vendor = conn.execute("SELECT name, lead_days FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            raise ToolError(f"Vendor {vendor_id} does not exist.")
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            raise ToolError(f"SKU {sku!r} size {size!r} is not in inventory.")
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            raise ToolError(f"SKU {sku!r} has no pricing record.")
        open_invoices = [r["id"] for r in conn.execute(
            "SELECT id FROM invoices WHERE vendor_id = ? AND status = 'open'", (vendor_id,)
        )]
        if open_invoices:
            raise ToolError(f"Refused: {vendor['name']} has open invoice(s) {open_invoices} and will not ship until paid.")
        amount = round(price["unit_cost"] * qty, 2)
        before, after = debit_cash(conn, account, amount, today)
        payment_id = record_payment(conn, "purchase_order", vendor_id, amount, account, today, approved_by)

    return {
        "status": "ordered",
        "payment_id": payment_id,
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "sku": sku,
        "size": size,
        "qty": qty,
        "amount": amount,
        "account": account,
        "paid_at": today.isoformat(),
        "approved_by": approved_by,
        "expected_arrival": (today + timedelta(days=vendor["lead_days"])).isoformat(),
        "balance_before": before,
        "balance_after": after,
    }


if __name__ == "__main__":
    mcp.run(show_banner=False)
