"""Importing this package builds and registers all five agents."""

from backend.agents.accounting import accounting_agent
from backend.agents.boss import boss_agent
from backend.agents.customer_service import customer_service_agent
from backend.agents.facilities import facilities_agent
from backend.agents.inventory import inventory_agent

__all__ = ["accounting_agent", "boss_agent", "customer_service_agent", "facilities_agent", "inventory_agent"]
