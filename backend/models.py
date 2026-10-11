"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]


class PaymentRequest(BaseModel):
    """A payment prepared by the prepare_payment MCP tool. Never executed without human approval."""

    kind: Literal["invoice", "rent"]
    ref_id: int = Field(description="invoices.id for kind='invoice', leases.id for kind='rent'")
    payee: str
    amount: float
    account: str
    status: Literal["awaiting_human_approval", "refused"]
    reason: str = Field(description="Why this payment is needed, or why it was refused")


class PurchaseOrderRequest(BaseModel):
    """A restock order prepared by the prepare_purchase_order MCP tool. Never placed without human approval."""

    vendor_id: int
    vendor_name: str
    sku: str
    size: str
    qty: int
    total_cost: float
    lead_days: int
    expected_arrival: str | None = Field(description="Only if the tool reported one; None while blocked")
    status: Literal["awaiting_human_approval", "blocked", "refused"]
    reason: str


class MessageDraft(BaseModel):
    """A customer- or vendor-facing message. Drafted only; never sent."""

    to: str
    subject: str
    body: str


class AgentReport(BaseModel):
    """What a specialist agent hands back to whoever delegated to it."""

    agent: AgentName
    summary: str
    facts: list[str] = Field(default_factory=list, description="Facts confirmed by MCP tool results, with their source tool")
    payment_requests: list[PaymentRequest] = Field(default_factory=list)
    purchase_orders: list[PurchaseOrderRequest] = Field(default_factory=list)
    message_drafts: list[MessageDraft] = Field(default_factory=list)
    open_issues: list[str] = Field(default_factory=list, description="Anything unresolved or needing a human decision")


class TicketResolution(BaseModel):
    """The Boss Agent's final decision for one ticket."""

    ticket_id: int
    ticket_type: str
    assigned_agents: list[AgentName]
    decision: str = Field(description="The Boss's final decision in plain language")
    recommended_status: Literal["awaiting_approval", "blocked", "resolved", "needs_human"]
    payment_requests: list[PaymentRequest] = Field(default_factory=list)
    purchase_orders: list[PurchaseOrderRequest] = Field(default_factory=list)
    message_drafts: list[MessageDraft] = Field(default_factory=list)
    open_issues: list[str] = Field(default_factory=list)


@dataclass
class TicketBudget:
    """Mutable state shared by every agent working on the same ticket."""

    delegations: int = 0
    proposals: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TeamDeps:
    """Dependencies passed into every agent run."""

    run_id: str
    ticket_id: int | None
    agent: AgentName
    depth: int = 0
    chain: tuple[AgentName, ...] = ()
    budget: TicketBudget = field(default_factory=TicketBudget)


# ------------------------------------------------------------- backend API

ApprovalStatus = Literal["pending", "blocked", "refused", "approved"]


class Approval(BaseModel):
    """A payment or purchase order prepared by the agents, waiting on (or decided by) a human."""

    id: str
    item_type: Literal["payment", "purchase_order"]
    ticket_id: int | None
    run_id: str
    prepared_by: str | None
    status: ApprovalStatus = Field(description="pending = can be approved; blocked/refused = prepare tool said no")
    proposal: dict[str, Any] = Field(description="The prepare_payment / prepare_purchase_order tool result")
    created_at: str
    approved_by: str | None = None
    approved_at: str | None = None
    execution: dict[str, Any] | None = Field(default=None, description="execute_* tool result once paid")


class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human approving this payment")


class DecisionRequest(BaseModel):
    """A human's answer to a judgment call the agents flagged (e.g. which discount to grant)."""

    decided_by: str = Field(min_length=1)
    decision: str = Field(min_length=1)


class RunStatus(BaseModel):
    run_id: str
    ticket_id: int
    status: Literal["running", "completed", "failed"]
    started_at: str
    finished_at: str | None = None
    error: str | None = None
    resolution: TicketResolution | None = None
