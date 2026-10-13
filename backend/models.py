"""Shared Pydantic schemas and per-workflow dependencies for the agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


AgentRole = Literal[
    "boss",
    "inventory",
    "accounting",
    "facilities",
    "customer_service",
]

AGENT_ROLES: tuple[AgentRole, ...] = (
    "boss",
    "inventory",
    "accounting",
    "facilities",
    "customer_service",
)


class AgentFact(BaseModel):
    """A statement tied to one or more results returned by an MCP tool."""

    statement: str
    source_tools: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class MessageDraft(BaseModel):
    """A message draft kept for a human; it is never sent by an agent."""

    recipient_type: Literal["customer", "vendor", "landlord"]
    recipient: str | None = None
    subject: str | None = None
    body: str
    status: Literal["draft_only"] = "draft_only"


class ApprovalRequest(BaseModel):
    """A proposed business action for the human approval board."""

    action_type: Literal["payment", "purchase_order", "discount", "other"]
    summary: str
    reference_id: int | None = None
    amount: float | None = None
    reason: str
    requires_human_approval: Literal[True] = True
    payment_kind: Literal["invoice", "rent"] | None = None
    sku: str | None = None
    size: str | None = None
    quantity: int | None = None
    unit_cost: float | None = None
    vendor_id: int | None = None


class AgentReport(BaseModel):
    """Structured findings, drafts, and recommendations from one agent run."""

    summary: str
    facts: list[AgentFact] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    drafts: list[MessageDraft] = Field(default_factory=list)
    approval_requests: list[ApprovalRequest] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    status: Literal[
        "analysis_complete",
        "waiting_for_human",
        "needs_information",
        "blocked",
    ] = "analysis_complete"


class AgentWorkflowResult(BaseModel):
    """Final Boss decision for a board or ticket workflow."""

    run_id: str
    ticket_id: int | None = None
    status: Literal["analysis_complete", "waiting_for_human", "needs_information", "blocked"]
    boss_report: AgentReport
    agent_reports: list[AgentReport] = Field(default_factory=list)
    agent_invocations: int
    mcp_tool_calls: int
    model_id: str


class AuditEvent(BaseModel):
    """One append-only audit entry; never includes provider credentials."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str
    step: int
    event_type: str
    agent: AgentRole | None = None
    parent_agent: AgentRole | None = None
    ticket_id: int | None = None
    delegation_depth: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


@dataclass
class WorkflowState:
    """Mutable counters shared by agents participating in one workflow."""

    run_id: str
    ticket_id: int | None
    step_number: int = 0
    agent_invocations: int = 0
    mcp_tool_calls: int = 0
    reports: list[AgentReport] = field(default_factory=list)

    def next_step(self) -> int:
        self.step_number += 1
        return self.step_number


@dataclass
class AgentDependencies:
    """PydanticAI dependencies for MCP calls, delegation, and audit logging."""

    team: Any
    mcp_client: Any
    audit_trail: Any
    workflow: WorkflowState
    role: AgentRole
    ticket_id: int | None
    delegation_depth: int
    parent_agent: AgentRole | None
    agent_stack: tuple[AgentRole, ...]
