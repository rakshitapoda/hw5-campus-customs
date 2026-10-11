"""Facilities Agent: shop space, leases, and rent."""

from __future__ import annotations

from backend.models import AgentReport
from backend.team import make_agent

MCP_TOOLS = {"get_shop_date", "get_ticket", "get_lease"}

facilities_agent = make_agent("facilities", AgentReport, MCP_TOOLS)
