"""PydanticAI functions that forward requests to the FastMCP server only."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from .audit import audit_safe
from .models import AgentDependencies

async def _call_mcp(
    ctx: RunContext[AgentDependencies],
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    deps = ctx.deps
    deps.workflow.mcp_tool_calls += 1
    deps.audit_trail.record(
        deps.workflow,
        "mcp_tool_started",
        agent=deps.role,
        parent_agent=deps.parent_agent,
        ticket_id=deps.ticket_id,
        delegation_depth=deps.delegation_depth,
        details={"tool_name": tool_name, "arguments": arguments},
    )
    try:
        result = await deps.mcp_client.call_tool(tool_name, arguments)
    except Exception as exc:
        deps.audit_trail.record(
            deps.workflow,
            "mcp_tool_failed",
            agent=deps.role,
            parent_agent=deps.parent_agent,
            ticket_id=deps.ticket_id,
            delegation_depth=deps.delegation_depth,
            details={"tool_name": tool_name, "error_type": type(exc).__name__},
        )
        raise
    deps.audit_trail.record(
        deps.workflow,
        "mcp_tool_completed",
        agent=deps.role,
        parent_agent=deps.parent_agent,
        ticket_id=deps.ticket_id,
        delegation_depth=deps.delegation_depth,
        details={"tool_name": tool_name, "result": audit_safe(result)},
    )
    return result


async def get_customer_order_context(
    ctx: RunContext[AgentDependencies], ticket_id: int = 101
) -> dict[str, Any]:
    """Forward the customer-order lookup to the MCP server."""
    return await _call_mcp(ctx, "get_customer_order_context", {"ticket_id": ticket_id})


async def get_rent_ticket_context(
    ctx: RunContext[AgentDependencies], ticket_id: int = 102
) -> dict[str, Any]:
    """Forward the rent/lease lookup to the MCP server."""
    return await _call_mcp(ctx, "get_rent_ticket_context", {"ticket_id": ticket_id})


async def get_discount_request_context(
    ctx: RunContext[AgentDependencies], ticket_id: int = 103
) -> dict[str, Any]:
    """Forward the price-override lookup to the MCP server."""
    return await _call_mcp(ctx, "get_discount_request_context", {"ticket_id": ticket_id})


async def list_open_tickets(ctx: RunContext[AgentDependencies]) -> dict[str, Any]:
    """Forward the current open ticket board to the MCP server."""
    return await _call_mcp(ctx, "list_open_tickets", {})


async def get_inventory_for_sku(
    ctx: RunContext[AgentDependencies], sku: str
) -> dict[str, Any]:
    """Forward a SKU-wide inventory lookup to the MCP server."""
    return await _call_mcp(ctx, "get_inventory_for_sku", {"sku": sku})


async def list_vendor_capabilities(
    ctx: RunContext[AgentDependencies],
) -> dict[str, Any]:
    """Forward vendor specialty, lead-time, and open-invoice data to MCP."""
    return await _call_mcp(ctx, "list_vendor_capabilities", {})


async def assess_invoice_payment(
    ctx: RunContext[AgentDependencies],
    invoice_id: int,
    account_name: str = "checking",
) -> dict[str, Any]:
    """Forward a read-only invoice payment-capacity check to MCP."""
    return await _call_mcp(
        ctx,
        "assess_invoice_payment",
        {"invoice_id": invoice_id, "account_name": account_name},
    )


async def assess_lease_payment(
    ctx: RunContext[AgentDependencies],
    lease_id: int,
    account_name: str = "checking",
) -> dict[str, Any]:
    """Forward a read-only rent payment-capacity check to MCP."""
    return await _call_mcp(
        ctx,
        "assess_lease_payment",
        {"lease_id": lease_id, "account_name": account_name},
    )


MCP_AGENT_FUNCTIONS = (
    get_customer_order_context,
    get_rent_ticket_context,
    get_discount_request_context,
    list_open_tickets,
    get_inventory_for_sku,
    list_vendor_capabilities,
    assess_invoice_payment,
    assess_lease_payment,
)
