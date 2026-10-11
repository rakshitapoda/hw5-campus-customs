"""Boss Agent: reads each ticket, routes it, delegates, and makes the final decision."""

from __future__ import annotations

from backend.models import TicketResolution
from backend.team import make_agent

MCP_TOOLS = {"get_shop_date", "list_open_tickets", "get_ticket"}

boss_agent = make_agent("boss", TicketResolution, MCP_TOOLS)
