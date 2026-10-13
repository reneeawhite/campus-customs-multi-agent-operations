"""FastAPI routes for the Campus Customs dashboard and human approvals."""

from __future__ import annotations

import asyncio
import math
import sys
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Support the requested command when the current directory is backend/:
# uvicorn main:app --reload --port 8000
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.audit import AuditTrail
from backend.mcp_client import CampusCustomsMCPClient, MCPToolError
from backend.models import ApprovalRequest, WorkflowState
from backend.team import AgentTeam


app = FastAPI(
    title="Campus Customs API",
    version="1.0.0",
    description="Ticket, agent, cash, approval, and reset routes for the local dashboard.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://localhost:5173",
        "https://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

audit_trail = AuditTrail()
workflow_lock = asyncio.Lock()


class HumanApproval(BaseModel):
    approved_by: str = Field(min_length=1, max_length=120)
    account_name: str = Field(default="checking", min_length=1, max_length=80)
    vendor_id: int | None = Field(default=None, gt=0)
    vendor_match_confirmed: bool = False


class PendingApproval(BaseModel):
    approval_id: str
    run_id: str
    ticket_id: int
    agent: str
    request: ApprovalRequest
    status: Literal["pending", "approved"] = "pending"
    result: dict[str, Any] | None = None


@app.on_event("startup")
async def initialize_runtime_state() -> None:
    app.state.pending_approvals = {}


async def _mcp_call(tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        async with CampusCustomsMCPClient() as client:
            return await client.call_tool(tool_name, arguments or {})
    except MCPToolError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _record_api_event(
    event_type: str,
    *,
    ticket_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    workflow = WorkflowState(run_id=f"api-{uuid4()}", ticket_id=ticket_id)
    audit_trail.record(
        workflow,
        event_type,
        ticket_id=ticket_id,
        details=details,
    )


def _approvals_from_audit(result_run_id: str) -> list[PendingApproval]:
    pending_by_key: dict[tuple[Any, ...], PendingApproval] = {}
    for event in audit_trail.recent_events(1_000):
        if event.get("run_id") != result_run_id or event.get("event_type") != "agent_completed":
            continue
        details = event.get("details") or {}
        report = details.get("report") or {}
        for raw_request in report.get("approval_requests", []):
            request = ApprovalRequest.model_validate(raw_request)
            if request.action_type not in {"payment", "purchase_order"}:
                continue
            ticket_id = event.get("ticket_id")
            if ticket_id is None:
                continue
            key = (
                ticket_id,
                request.action_type,
                request.payment_kind,
                request.reference_id,
                request.amount,
                request.sku,
                request.size,
                request.quantity,
                request.unit_cost,
            )
            agent = event.get("agent") or "team"
            existing = pending_by_key.get(key)
            if existing is None or (agent == "boss" and existing.agent != "boss"):
                pending_by_key[key] = PendingApproval(
                    approval_id=str(uuid4()),
                    run_id=result_run_id,
                    ticket_id=ticket_id,
                    agent=agent,
                    request=request,
                )
    return list(pending_by_key.values())


@app.get("/api/tickets")
async def get_tickets() -> dict[str, Any]:
    """Return ticket IDs, current statuses, and fields needed by the dashboard."""
    result = await _mcp_call("list_tickets")
    tickets = []
    for ticket in result.get("tickets", []):
        status = str(ticket.get("status", "")).casefold()
        tickets.append(
            {
                "id": ticket["id"],
                "type": ticket["type"],
                "subject": ticket["subject"],
                "status": ticket["status"],
                "is_open": status == "open",
                "is_resolved": status in {"resolved", "closed"},
                "sku": ticket.get("sku"),
                "size": ticket.get("size"),
                "quantity": ticket.get("qty"),
                "lease_id": ticket.get("lease_id"),
                "invoice_id": ticket.get("invoice_id"),
            }
        )
    return {"shop_date": result.get("shop_date"), "tickets": tickets}


@app.post("/api/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int) -> dict[str, Any]:
    """Run Boss and its delegated specialists for one ticket; return reports and approvals."""
    if ticket_id <= 0:
        raise HTTPException(status_code=422, detail="ticket_id must be positive")
    async with workflow_lock:
        try:
            async with CampusCustomsMCPClient() as client:
                result = await AgentTeam(client, audit_trail).run_ticket(ticket_id)
        except MCPToolError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Agent workflow could not start ({type(exc).__name__}).",
            ) from exc

        approvals = _approvals_from_audit(
            result.run_id,
        )
        queue = app.state.pending_approvals
        for approval in approvals:
            queue[approval.approval_id] = approval
        return {
            "workflow": result.model_dump(mode="json"),
            "pending_approvals": [item.model_dump(mode="json") for item in approvals],
        }


@app.get("/api/events")
async def get_recent_events(
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """Return recent agent reports, delegation events, and MCP tool-use events."""
    return {"events": audit_trail.recent_events(limit)}


@app.get("/api/approvals")
async def get_approvals() -> dict[str, Any]:
    """List proposals created by agent runs for the human approval board."""
    approvals = list(app.state.pending_approvals.values())
    return {"approvals": [item.model_dump(mode="json") for item in approvals]}


async def _verify_payment_proposal(
    client: CampusCustomsMCPClient,
    approval: PendingApproval,
    account_name: str,
) -> tuple[str, float]:
    request = approval.request
    if request.action_type != "payment" or request.reference_id is None:
        raise HTTPException(status_code=409, detail="This approval is not a complete payment proposal.")
    if request.payment_kind == "invoice":
        assessment = await client.call_tool(
            "assess_invoice_payment",
            {"invoice_id": request.reference_id, "account_name": account_name},
        )
        payable_amount = float(assessment["invoice"]["amount"])
    elif request.payment_kind == "rent":
        assessment = await client.call_tool(
            "assess_lease_payment",
            {"lease_id": request.reference_id, "account_name": account_name},
        )
        payable_amount = float(assessment["lease"]["monthly_rent"])
    else:
        raise HTTPException(
            status_code=409,
            detail="Payment proposal must identify an invoice or rent lease.",
        )
    if request.amount is None or not math.isclose(
        float(request.amount), payable_amount, rel_tol=0, abs_tol=0.005
    ):
        raise HTTPException(
            status_code=409,
            detail="Proposed amount no longer matches the recorded amount; rerun the ticket.",
        )
    if not assessment.get("can_cover_amount"):
        raise HTTPException(
            status_code=409,
            detail="Current cash is insufficient; payment was not made.",
        )
    return request.payment_kind, payable_amount


async def _verify_purchase_proposal(
    client: CampusCustomsMCPClient,
    approval: PendingApproval,
    vendor_id: int,
) -> None:
    request = approval.request
    if (
        request.action_type != "purchase_order"
        or request.reference_id != approval.ticket_id
        or not request.sku
        or not request.size
        or request.quantity is None
        or request.unit_cost is None
        or request.amount is None
    ):
        raise HTTPException(
            status_code=409,
            detail="The agent proposal lacks MCP-sourced SKU, size, quantity, unit cost, or amount.",
        )
    context_tools = {
        "customer_order": "get_customer_order_context",
        "price_override": "get_discount_request_context",
    }
    tickets = await client.call_tool("list_tickets", {})
    ticket = next(
        (item for item in tickets.get("tickets", []) if item["id"] == approval.ticket_id),
        None,
    )
    if ticket is None or ticket["status"].casefold() != "open":
        raise HTTPException(status_code=409, detail="The source ticket is not open.")
    context_tool = context_tools.get(ticket["type"])
    if context_tool is None:
        raise HTTPException(status_code=409, detail="This ticket type has no supported purchase context.")
    context = await client.call_tool(context_tool, {"ticket_id": approval.ticket_id})
    actual_ticket = context["ticket"]
    if (request.sku, request.size) != (actual_ticket["sku"], actual_ticket["size"]):
        raise HTTPException(status_code=409, detail="Proposal SKU/size differs from the ticket.")
    stock = context.get("inventory")
    pricing = context.get("pricing")
    if stock is None or pricing is None or actual_ticket.get("qty") is None:
        raise HTTPException(status_code=409, detail="MCP lacks the stock or cost needed for this PO.")
    shortfall = max(0, int(actual_ticket["qty"]) - int(stock["qty"]))
    unit_cost = float(pricing["unit_cost"])
    amount = shortfall * unit_cost
    if (
        shortfall <= 0
        or request.quantity != shortfall
        or not math.isclose(float(request.unit_cost), unit_cost, rel_tol=0, abs_tol=0.005)
        or not math.isclose(float(request.amount), amount, rel_tol=0, abs_tol=0.005)
    ):
        raise HTTPException(
            status_code=409,
            detail="Proposal no longer matches the recorded shortfall and cost; rerun the ticket.",
        )
    vendors = await client.call_tool("list_vendor_capabilities", {})
    vendor = next(
        (
            item
            for item in vendors.get("vendors", [])
            if int(item["vendor"]["id"]) == vendor_id
        ),
        None,
    )
    if vendor is None:
        raise HTTPException(status_code=409, detail="Selected vendor is not in the database.")
    if not vendor.get("can_ship_new_product"):
        raise HTTPException(
            status_code=409,
            detail="Selected vendor has an open unpaid invoice and cannot ship new product.",
        )


@app.post("/api/approvals/{approval_id}/approve")
async def approve_agent_proposal(
    approval_id: str,
    body: HumanApproval,
) -> dict[str, Any]:
    """Record a human-approved unsent PO, or execute a human-approved payment."""
    approval = app.state.pending_approvals.get(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request was not found.")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="This approval request was already handled.")

    _record_api_event(
        "human_approval_requested",
        ticket_id=approval.ticket_id,
        details={
            "approval_id": approval_id,
            "action_type": approval.request.action_type,
            "reference_id": approval.request.reference_id,
        },
    )
    async with workflow_lock:
        try:
            async with CampusCustomsMCPClient() as client:
                if approval.request.action_type == "payment":
                    payment_kind, _ = await _verify_payment_proposal(
                        client, approval, body.account_name
                    )
                    result = await client.call_tool(
                        "approve_payment",
                        {
                            "kind": payment_kind,
                            "reference_id": approval.request.reference_id,
                            "approved_by": body.approved_by,
                            "account_name": body.account_name,
                        },
                    )
                elif approval.request.action_type == "purchase_order":
                    if body.vendor_id is None:
                        raise HTTPException(
                            status_code=422,
                            detail="Select a vendor from the database before approving the PO draft.",
                        )
                    await _verify_purchase_proposal(client, approval, body.vendor_id)
                    if not body.vendor_match_confirmed:
                        raise HTTPException(
                            status_code=422,
                            detail="Confirm the vendor choice; the database has no SKU-to-vendor link.",
                        )
                    result = await client.call_tool(
                        "approve_purchase_order",
                        {
                            "ticket_id": approval.ticket_id,
                            "sku": approval.request.sku,
                            "size": approval.request.size,
                            "quantity": approval.request.quantity,
                            "vendor_id": body.vendor_id,
                            "approved_by": body.approved_by,
                            "vendor_match_confirmed": body.vendor_match_confirmed,
                        },
                    )
                else:
                    raise HTTPException(
                        status_code=409,
                        detail="Only payment and purchase-order proposals can be approved here.",
                    )
        except HTTPException as exc:
            _record_api_event(
                "human_approval_failed",
                ticket_id=approval.ticket_id,
                details={"approval_id": approval_id, "status_code": exc.status_code},
            )
            raise
        except MCPToolError as exc:
            _record_api_event(
                "human_approval_failed",
                ticket_id=approval.ticket_id,
                details={"approval_id": approval_id, "error_type": type(exc).__name__},
            )
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    approval.status = "approved"
    approval.result = result
    _record_api_event(
        "human_approval_completed",
        ticket_id=approval.ticket_id,
        details={
            "approval_id": approval_id,
            "action_type": approval.request.action_type,
            "reference_id": approval.request.reference_id,
            "result": result,
        },
    )
    return {"approval": approval.model_dump(mode="json")}


@app.get("/api/purchase-orders")
async def get_purchase_orders() -> dict[str, Any]:
    """List approved unsent purchase orders and their payment state."""
    return await _mcp_call("list_purchase_orders")


@app.get("/api/vendors")
async def get_vendors() -> dict[str, Any]:
    """Return recorded vendor choices and shipping blocks for a human PO review."""
    return await _mcp_call("list_vendor_capabilities")


@app.post("/api/purchase-orders/{purchase_order_id}/pay")
async def pay_purchase_order(
    purchase_order_id: int,
    body: HumanApproval,
) -> dict[str, Any]:
    """Make a separate human-approved PO payment; cash is not spent at PO approval."""
    if purchase_order_id <= 0:
        raise HTTPException(status_code=422, detail="purchase_order_id must be positive")
    async with workflow_lock:
        result = await _mcp_call(
            "approve_payment",
            {
                "kind": "purchase_order",
                "reference_id": purchase_order_id,
                "approved_by": body.approved_by,
                "account_name": body.account_name,
            },
        )
    _record_api_event(
        "purchase_order_payment_completed",
        details={"purchase_order_id": purchase_order_id, "result": result},
    )
    return result


@app.get("/api/cash/checking")
async def get_checking_balance() -> dict[str, Any]:
    """Return the current checking balance from the working database."""
    return await _mcp_call("get_cash_balance", {"account_name": "checking"})


@app.post("/api/reset")
async def reset_database() -> dict[str, Any]:
    """Reset the working copy from the original and clear in-memory approval proposals."""
    async with workflow_lock:
        result = await _mcp_call("reset_working_database")
        app.state.pending_approvals.clear()
    _record_api_event("database_reset", details=result)
    return result
