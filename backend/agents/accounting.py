"""Accounting Agent: cash, invoices, margins, and payments / purchase orders prepared for human approval."""

from __future__ import annotations

from backend.models import AgentReport
from backend.team import make_agent

MCP_TOOLS = {
    "get_shop_date",
    "get_ticket",
    "get_cash_balance",
    "get_invoice",
    "check_vendor_status",
    "check_margin",
    "prepare_payment",
    "prepare_purchase_order",
}

accounting_agent = make_agent("accounting", AgentReport, MCP_TOOLS)
