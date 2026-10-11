"""Inventory Agent: stock by SKU and size, shortages, and which vendor can restock."""

from __future__ import annotations

from backend.models import AgentReport
from backend.team import make_agent

MCP_TOOLS = {"get_shop_date", "get_ticket", "check_inventory", "check_vendor_status"}

inventory_agent = make_agent("inventory", AgentReport, MCP_TOOLS)
