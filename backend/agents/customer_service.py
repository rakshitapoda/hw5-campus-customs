"""Customer Service Agent: drafts customer-facing messages (never sends them)."""

from __future__ import annotations

from backend.models import AgentReport
from backend.team import make_agent

MCP_TOOLS = {"get_shop_date", "get_ticket", "check_inventory"}

customer_service_agent = make_agent("customer_service", AgentReport, MCP_TOOLS)
