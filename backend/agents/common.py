"""Shared construction rules for the five distinct PydanticAI agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext

from ..mcp_tools import MCP_AGENT_FUNCTIONS
from ..models import AgentDependencies, AgentReport, AgentRole


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
COMMON_POLICY = """
You are one member of the Campus Customs shop team. Treat the MCP server as the
only source of shop, stock, lease, vendor, invoice, cash, and ticket facts. Never
invent or infer a missing database value; say when a link or value is absent.
Use desk.date_today for due-date decisions. Do not contact anyone, send messages,
place orders, make payments, change ticket status, or claim an action happened.
All communication is a draft. All payments, purchase orders, discounts, and
other commitments require human approval. If money is discussed, use the
read-only MCP assessment tools and preserve the no-negative-balance rule.
Delegate to another role when its expertise is useful, cite MCP tool names in
facts, keep the report concise, and return only the structured AgentReport.
Delegation is peer-to-peer: any active role may call `delegate_to_agent`
directly for any other role. Do not route a specialist request through Boss
just to relay it. Return the delegated report to the agent that called you;
Boss alone makes the final ticket recommendation. Delegate only for a needed,
bounded task that another role can answer, and avoid duplicate work or cycles.
In summaries, facts, and recommendations, refer to a person by ticket role or
ticket ID instead of repeating personal names or contact details. Customer
drafts should use a generic greeting and must not include recipient addresses.

Choose tools from the ticket's actual `type` and populated fields, not from its
ID or a remembered example. If the type is not in the task, call
`list_open_tickets` and find the row by ID before choosing a context tool. Use
`get_customer_order_context` for `customer_order`, `get_rent_ticket_context`
for `rent_notice`, and `get_discount_request_context` for `price_override`. Pass
the ticket ID returned by MCP explicitly; the context tools' default IDs are
only for the original sample tickets. Use `get_inventory_for_sku` for other
size rows, `list_vendor_capabilities` for vendor lead times and open invoices,
and `assess_invoice_payment` or `assess_lease_payment` only with matching IDs
returned by MCP. If a ticket type or needed lookup is not supported by the
available MCP tools, report the missing capability and ask Boss or a human to
add/perform that lookup. Never force an unrelated context tool or fill the gap
with a guess.
""".strip()


def build_agent(role: AgentRole, model: Any) -> Agent[AgentDependencies, AgentReport]:
    """Load one role prompt and attach only MCP-backed data tools."""
    prompt_path = PROMPT_DIR / f"{role}.md"
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt for agent {role!r} is missing: {prompt_path}")
    role_prompt = prompt_path.read_text(encoding="utf-8").strip()
    agent = Agent(
        model,
        name=role,
        deps_type=AgentDependencies,
        output_type=AgentReport,
        system_prompt=f"{COMMON_POLICY}\n\n{role_prompt}",
        retries=1,
    )
    for tool_function in MCP_AGENT_FUNCTIONS:
        agent.tool(tool_function)
    agent.tool(_delegation_tool(role))
    return agent


def _delegation_tool(owner: AgentRole):
    async def delegate_to_agent(
        ctx: RunContext[AgentDependencies],
        target_agent: AgentRole,
        task: str,
        ticket_id: int | None = None,
    ) -> AgentReport:
        """Ask any other role for help; the workflow enforces loop and call caps."""
        return await ctx.deps.team.delegate_task(
            ctx=ctx,
            owner=owner,
            target_agent=target_agent,
            task=task,
            ticket_id=ticket_id,
        )

    delegate_to_agent.__name__ = "delegate_to_agent"
    delegate_to_agent.__doc__ = (
        f"Delegate a bounded task from {owner} to any other Campus Customs agent. "
        "Set ticket_id when the task concerns one ticket."
    )
    return delegate_to_agent
