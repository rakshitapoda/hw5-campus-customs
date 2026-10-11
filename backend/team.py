"""Shared plumbing for the Campus Customs agent team.

- Every agent uses gpt-6-luna through Portkey (PORTKEY_API_KEY). No other model is used.
- All shop data comes from the campus-customs MCP server (mcp_server/server.py),
  which reads data/campus_customs_new.db. Agents have no other path to the data.
- Any agent can delegate to any other agent through the delegate_task tool.
- Every step of every agent loop is appended to output/audit_trail.json.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext, UsageLimits
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from backend.audit import append_event
from backend.models import AgentName, AgentReport, TeamDeps, TicketResolution

ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT_DIR / "backend" / "prompts"
MCP_SERVER_PATH = ROOT_DIR / "mcp_server" / "server.py"

load_dotenv(ROOT_DIR / ".env")

MODEL_NAME = "gpt-6-luna"  # the only model allowed in this assignment
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")

# Token / loop limits (shared by every agent working on the same ticket).
MAX_OUTPUT_TOKENS = 4000        # per model response (includes reasoning tokens)
MAX_REQUESTS_PER_TICKET = 40    # model calls across all agents on one ticket
MAX_TOOL_CALLS_PER_TICKET = 60
MAX_TOKENS_PER_TICKET = 250_000
MAX_DELEGATION_DEPTH = 3        # boss -> agent -> agent -> agent
MAX_DELEGATIONS_PER_TICKET = 8
MAX_RETRIES = 2                 # per tool / output validation
MODEL_TIMEOUT_SECONDS = 120     # per model HTTP request
MODEL_HTTP_RETRIES = 1

USAGE_LIMITS = UsageLimits(
    request_limit=MAX_REQUESTS_PER_TICKET,
    tool_calls_limit=MAX_TOOL_CALLS_PER_TICKET,
    total_tokens_limit=MAX_TOKENS_PER_TICKET,
)

AGENTS: dict[str, Agent[TeamDeps, Any]] = {}
AGENT_MCP_TOOLS: dict[str, list[str]] = {}


class AgentNotConfigured(RuntimeError):
    pass


def build_model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise AgentNotConfigured("PORTKEY_API_KEY is not set (environment or .env).")
    client = AsyncOpenAI(
        base_url=PORTKEY_BASE_URL,
        api_key=api_key,
        timeout=MODEL_TIMEOUT_SECONDS,
        max_retries=MODEL_HTTP_RETRIES,
        # Always ask for a fresh completion: a cached reply would replay an earlier run's
        # answer instead of reading the current database.
        default_headers={"x-portkey-cache-force-refresh": "true"},
    )
    # Responses API: this Portkey route rejects function tools on chat completions while reasoning is on.
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


# One MCP connection shared by all agents; each agent sees a filtered subset of its tools.
MCP_TOOLSET = MCPToolset(
    Client(StdioTransport(command=sys.executable, args=[str(MCP_SERVER_PATH)], cwd=str(ROOT_DIR))),
    max_retries=MAX_RETRIES,
)


# ---------------------------------------------------------------- delegation

async def delegate_task(ctx: RunContext[TeamDeps], to_agent: AgentName, task: str) -> str:
    """Hand a task to another Campus Customs agent and get its report back (JSON).

    Agents: boss (routing, final decisions), inventory (stock by SKU/size, restock
    vendors), accounting (cash, invoices, margins, payment / purchase-order
    preparation), facilities (leases and rent), customer_service (customer-facing
    message drafts). Give the task enough context (ticket id, SKU, size, qty, amounts
    already confirmed) for the other agent to work on its own.
    """
    deps = ctx.deps
    refusal = None
    if to_agent == deps.agent:
        refusal = "You cannot delegate to yourself."
    elif to_agent in deps.chain:
        refusal = f"{to_agent} is already working on this request higher up the chain; answer from what you have."
    elif deps.depth + 1 > MAX_DELEGATION_DEPTH:
        refusal = f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached; answer from what you have."
    elif deps.budget.delegations >= MAX_DELEGATIONS_PER_TICKET:
        refusal = f"Delegation limit ({MAX_DELEGATIONS_PER_TICKET} per ticket) reached; answer from what you have."
    if refusal:
        append_event("delegation_refused", **_where(deps), to_agent=to_agent, task=task, reason=refusal)
        return f"Refused: {refusal}"

    deps.budget.delegations += 1
    append_event("delegation", **_where(deps), to_agent=to_agent, task=task)
    child = TeamDeps(
        run_id=deps.run_id,
        ticket_id=deps.ticket_id,
        agent=to_agent,
        depth=deps.depth + 1,
        chain=(*deps.chain, to_agent),
        budget=deps.budget,
    )
    output = await run_agent(to_agent, f"Task from the {deps.agent} agent (ticket {deps.ticket_id}):\n{task}", child, usage=ctx.usage)
    return output.model_dump_json()


# ---------------------------------------------------- proposal guardrails

PROPOSAL_TOOLS = {"prepare_payment", "prepare_purchase_order"}


def proposals_note(ctx: RunContext[TeamDeps]) -> str:
    """Dynamic instruction: proposals already prepared earlier in this run."""
    proposals = ctx.deps.budget.proposals
    if not proposals:
        return "No payments or purchase orders have been prepared yet in this run."
    pending = sum(
        p.get("amount", p.get("total_cost", 0)) for p in proposals if p.get("status") == "awaiting_human_approval"
    )
    keys = ("prepared_for_ticket", "prepared_by", "kind", "ref_id", "vendor_id", "sku", "size", "qty", "amount", "total_cost", "status")
    lines = [json.dumps({k: p[k] for k in keys if p.get(k) is not None}) for p in proposals]
    return (
        "Payments / purchase orders prepared so far in this run, each listed once. If one of these shows up in a "
        "teammate's report, it is the same item, not a duplicate. Do not call prepare_payment / "
        "prepare_purchase_order again for an item listed here; for new items pass "
        f"pending_total={pending:.2f}:\n" + "\n".join(lines)
    )


def proposal_key(p: dict) -> tuple:
    if "kind" in p:
        return ("payment", p["kind"], p["ref_id"])
    return ("purchase_order", p.get("vendor_id"), p.get("sku"), p.get("size"), p.get("qty"))


def record_proposal(deps: TeamDeps, proposal: dict) -> None:
    """Remember a prepare_* result for this run; re-preparing the same item replaces the old entry."""
    proposal = {**proposal, "prepared_for_ticket": deps.ticket_id, "prepared_by": deps.agent}
    proposals = deps.budget.proposals
    proposals[:] = [p for p in proposals if proposal_key(p) != proposal_key(proposal)]
    proposals.append(proposal)


def _matches(item: BaseModel, keys: tuple[str, ...], proposals: list[dict]) -> bool:
    data = item.model_dump()
    return any(all(p.get(k) == data[k] for k in keys) for p in proposals)


async def validate_proposals(ctx: RunContext[TeamDeps], output: AgentReport | TicketResolution):
    """Reject any payment or purchase order that was not produced by the MCP prepare tools."""
    proposals = ctx.deps.budget.proposals
    for pay in output.payment_requests:
        if not _matches(pay, ("kind", "ref_id", "amount", "status"), proposals):
            raise ModelRetry(
                f"Payment request {pay.kind} #{pay.ref_id} (${pay.amount}) does not match any prepare_payment "
                "tool result. Only include payments exactly as returned by prepare_payment."
            )
    for po in output.purchase_orders:
        if not _matches(po, ("vendor_id", "sku", "size", "qty", "total_cost", "status"), proposals):
            raise ModelRetry(
                f"Purchase order {po.sku} {po.size} x{po.qty} does not match any prepare_purchase_order tool "
                "result. Only include purchase orders exactly as returned by prepare_purchase_order."
            )
    return output


# ------------------------------------------------------------ agent factory

def make_agent(name: AgentName, output_type: type[BaseModel], mcp_tools: set[str]) -> Agent[TeamDeps, Any]:
    """Build one agent with its own prompt file, its own model instance, and its MCP tool subset."""
    agent = Agent(
        build_model(),
        name=name,
        output_type=output_type,
        instructions=(PROMPTS_DIR / f"{name}.md").read_text(),
        deps_type=TeamDeps,
        tools=[delegate_task],
        toolsets=[MCP_TOOLSET.filtered(lambda ctx, tool_def: tool_def.name in mcp_tools)],
        retries=MAX_RETRIES,
        model_settings=ModelSettings(max_tokens=MAX_OUTPUT_TOKENS),
    )
    agent.instructions(proposals_note)
    agent.output_validator(validate_proposals)
    AGENTS[name] = agent
    AGENT_MCP_TOOLS[name] = sorted(mcp_tools)
    return agent


# ------------------------------------------------------- audited agent loop

def _where(deps: TeamDeps) -> dict[str, Any]:
    return {"run_id": deps.run_id, "ticket_id": deps.ticket_id, "agent": deps.agent, "depth": deps.depth, "chain": list(deps.chain)}


def _content(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    return value


def _as_dict(value: Any) -> dict | None:
    value = _content(value)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return None
    return value if isinstance(value, dict) else None


async def run_agent(name: AgentName, prompt: str, deps: TeamDeps, usage=None) -> AgentReport | TicketResolution:
    """Run one agent, appending every step of its loop to the audit trail."""
    agent = AGENTS[name]
    where = _where(deps)
    append_event("agent_start", **where, model=MODEL_NAME, prompt=prompt)
    step = 0
    try:
        async with agent.iter(prompt, deps=deps, usage=usage, usage_limits=USAGE_LIMITS) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    step += 1
                    tool_results, retries = [], []
                    for part in node.request.parts:
                        if isinstance(part, ToolReturnPart):
                            tool_results.append({"tool": part.tool_name, "tool_call_id": part.tool_call_id, "result": _content(part.content)})
                            proposal = _as_dict(part.content) if part.tool_name in PROPOSAL_TOOLS else None
                            if proposal and "status" in proposal:
                                record_proposal(deps, proposal)
                        elif isinstance(part, RetryPromptPart):
                            retries.append({"tool": part.tool_name, "message": _content(part.content)})
                    append_event("model_request", **where, step=step, tool_results=tool_results, retries=retries)
                elif Agent.is_call_tools_node(node):
                    response = node.model_response
                    append_event(
                        "model_response",
                        **where,
                        step=step,
                        model_name=response.model_name,
                        text=" ".join(p.content for p in response.parts if isinstance(p, TextPart)) or None,
                        tool_calls=[{"tool": p.tool_name, "tool_call_id": p.tool_call_id, "args": p.args_as_dict()}
                                    for p in response.parts if isinstance(p, ToolCallPart)],
                        usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
                    )
            result = run.result
    except BaseException as exc:  # includes cancellation from the per-ticket timeout
        append_event("agent_error", **where, step=step, error=f"{type(exc).__name__}: {exc}")
        raise

    append_event(
        "agent_end",
        **where,
        steps=step,
        output=result.output.model_dump(),
        usage_so_far={"requests": result.usage.requests, "input_tokens": result.usage.input_tokens,
                      "output_tokens": result.usage.output_tokens, "tool_calls": result.usage.tool_calls},
    )
    return result.output
