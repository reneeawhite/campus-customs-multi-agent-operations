"""Bounded, fully connected PydanticAI team for Campus Customs tickets."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic_ai import RunContext, UsageLimits

from .agents import build_agents
from .audit import AuditTrail, task_fingerprint
from .models import (
    AGENT_ROLES,
    AgentDependencies,
    AgentReport,
    AgentRole,
    AgentWorkflowResult,
    WorkflowState,
)
from .provider import MODEL_ID, create_agent_model


MAX_DELEGATION_DEPTH = 3
MAX_AGENT_INVOCATIONS_PER_WORKFLOW = 12
# A tool round and its structured final report may each require a provider request.
MAX_MODEL_REQUESTS_PER_AGENT_RUN = 4
MAX_BOSS_MODEL_REQUESTS_PER_RUN = 6
MAX_TOOL_CALLS_PER_AGENT_RUN = 6
MAX_TASK_CHARS = 2_000


class AgentTeam:
    """Boss-led team; every agent has the same MCP tools and delegation graph."""

    def __init__(self, mcp_client: Any, audit_trail: AuditTrail | None = None) -> None:
        self.mcp_client = mcp_client
        self.audit_trail = audit_trail or AuditTrail()
        model = create_agent_model()
        self.agents = build_agents(model)

    async def run_open_board(self) -> AgentWorkflowResult:
        """Ask Boss to inspect and route the current board without changing it."""
        return await self._run_workflow(
            ticket_id=None,
            task=(
                "Review the current open Campus Customs board. Start by calling "
                "list_open_tickets, classify each ticket, delegate bounded work to "
                "the relevant specialists, reconcile their sourced findings, and "
                "return one final recommendation per ticket. Do not resolve tickets "
                "or carry out external or financial actions."
            ),
        )

    async def run_ticket(self, ticket_id: int) -> AgentWorkflowResult:
        """Ask Boss to coordinate one ticket and return a review-ready report."""
        if ticket_id <= 0:
            raise ValueError("ticket_id must be a positive database ID")
        return await self._run_workflow(
            ticket_id=ticket_id,
            task=(
                f"Review open Campus Customs ticket {ticket_id}. Load its data through "
                "the matching MCP context tool, delegate specialist checks as needed, "
                "and return a sourced final recommendation. Keep the ticket open if "
                "approval, missing information, or an external action remains."
            ),
        )

    async def _run_workflow(
        self, *, ticket_id: int | None, task: str
    ) -> AgentWorkflowResult:
        workflow = WorkflowState(run_id=str(uuid4()), ticket_id=ticket_id)
        self.audit_trail.record(
            workflow,
            "workflow_started",
            agent="boss",
            ticket_id=ticket_id,
            delegation_depth=0,
            details={"scope": "open_board" if ticket_id is None else "single_ticket", "model_id": MODEL_ID},
        )
        report = await self._run_agent(
            role="boss",
            task=task,
            workflow=workflow,
            ticket_id=ticket_id,
            depth=0,
            parent_agent=None,
            stack=(),
        )
        status = self._workflow_status(report, workflow.reports)
        self.audit_trail.record(
            workflow,
            "workflow_finished",
            agent="boss",
            ticket_id=ticket_id,
            delegation_depth=0,
            details={
                "status": status,
                "agent_invocations": workflow.agent_invocations,
                "mcp_tool_calls": workflow.mcp_tool_calls,
                "summary": self._clip(report.summary),
            },
        )
        return AgentWorkflowResult(
            run_id=workflow.run_id,
            ticket_id=ticket_id,
            status=status,
            boss_report=report,
            agent_reports=list(workflow.reports),
            agent_invocations=workflow.agent_invocations,
            mcp_tool_calls=workflow.mcp_tool_calls,
            model_id=MODEL_ID,
        )

    async def _run_agent(
        self,
        *,
        role: AgentRole,
        task: str,
        workflow: WorkflowState,
        ticket_id: int | None,
        depth: int,
        parent_agent: AgentRole | None,
        stack: tuple[AgentRole, ...],
    ) -> AgentReport:
        if role not in AGENT_ROLES:
            return self._blocked_report(f"Unknown agent role: {role}")
        if role in stack or depth > MAX_DELEGATION_DEPTH:
            report = self._blocked_report("Delegation cycle or depth limit reached.")
            self.audit_trail.record(
                workflow,
                "delegation_blocked",
                agent=parent_agent,
                parent_agent=parent_agent,
                ticket_id=ticket_id,
                delegation_depth=depth,
                details={"target_agent": role, "reason": "cycle_or_depth_limit"},
            )
            workflow.reports.append(report)
            return report
        if workflow.agent_invocations >= MAX_AGENT_INVOCATIONS_PER_WORKFLOW:
            report = self._blocked_report("Workflow agent-call budget reached.")
            self.audit_trail.record(
                workflow,
                "agent_budget_reached",
                agent=parent_agent,
                ticket_id=ticket_id,
                delegation_depth=depth,
                details={"target_agent": role, "limit": MAX_AGENT_INVOCATIONS_PER_WORKFLOW},
            )
            workflow.reports.append(report)
            return report

        workflow.agent_invocations += 1
        self.audit_trail.record(
            workflow,
            "agent_started",
            agent=role,
            parent_agent=parent_agent,
            ticket_id=ticket_id,
            delegation_depth=depth,
            details={
                **task_fingerprint(self._clip(task, MAX_TASK_CHARS)),
                "model_id": MODEL_ID,
                "invocation": workflow.agent_invocations,
            },
        )
        deps = AgentDependencies(
            team=self,
            mcp_client=self.mcp_client,
            audit_trail=self.audit_trail,
            workflow=workflow,
            role=role,
            ticket_id=ticket_id,
            delegation_depth=depth,
            parent_agent=parent_agent,
            agent_stack=stack + (role,),
        )
        try:
            result = await self.agents[role].run(
                task,
                deps=deps,
                usage_limits=UsageLimits(
                    request_limit=(
                        MAX_BOSS_MODEL_REQUESTS_PER_RUN
                        if role == "boss"
                        else MAX_MODEL_REQUESTS_PER_AGENT_RUN
                    ),
                    tool_calls_limit=MAX_TOOL_CALLS_PER_AGENT_RUN,
                ),
            )
            report: AgentReport = result.output
            workflow.reports.append(report)
            self.audit_trail.record(
                workflow,
                "agent_completed",
                agent=role,
                parent_agent=parent_agent,
                ticket_id=ticket_id,
                delegation_depth=depth,
                details={
                    "report": report.model_dump(mode="json"),
                    "usage": self._usage_summary(result),
                },
            )
            return report
        except Exception as exc:
            self.audit_trail.record(
                workflow,
                "agent_failed",
                agent=role,
                parent_agent=parent_agent,
                ticket_id=ticket_id,
                delegation_depth=depth,
                details={"error_type": type(exc).__name__},
            )
            report = self._blocked_report(
                f"{role} could not complete this step; human review is required."
            )
            workflow.reports.append(report)
            return report

    async def delegate_task(
        self,
        *,
        ctx: RunContext[AgentDependencies],
        owner: AgentRole,
        target_agent: AgentRole,
        task: str,
        ticket_id: int | None,
    ) -> AgentReport:
        """Run another role with shared budgets and an auditable parent link."""
        deps = ctx.deps
        selected_ticket = ticket_id if ticket_id is not None else deps.ticket_id
        bounded_task = task.strip()[:MAX_TASK_CHARS]
        if not bounded_task:
            return self._blocked_report("Delegated task was empty.")
        if target_agent == owner:
            return self._blocked_report("An agent cannot delegate to itself.")
        self.audit_trail.record(
            deps.workflow,
            "delegation_requested",
            agent=owner,
            parent_agent=deps.parent_agent,
            ticket_id=selected_ticket,
            delegation_depth=deps.delegation_depth,
            details={"target_agent": target_agent, "task": self._clip(bounded_task)},
        )
        report = await self._run_agent(
            role=target_agent,
            task=bounded_task,
            workflow=deps.workflow,
            ticket_id=selected_ticket,
            depth=deps.delegation_depth + 1,
            parent_agent=owner,
            stack=deps.agent_stack,
        )
        self.audit_trail.record(
            deps.workflow,
            "delegation_returned",
            agent=owner,
            parent_agent=deps.parent_agent,
            ticket_id=selected_ticket,
            delegation_depth=deps.delegation_depth,
            details={"target_agent": target_agent, "status": report.status, "summary": self._clip(report.summary)},
        )
        return report

    @staticmethod
    def _workflow_status(
        boss_report: AgentReport, reports: list[AgentReport]
    ) -> str:
        if any(report.status == "blocked" for report in reports):
            return "blocked"
        if any(
            report.status == "waiting_for_human"
            or report.approval_requests
            or report.drafts
            for report in reports
        ):
            return "waiting_for_human"
        if any(report.status == "needs_information" or report.open_questions for report in reports):
            return "needs_information"
        return boss_report.status

    @staticmethod
    def _blocked_report(summary: str) -> AgentReport:
        return AgentReport(summary=summary, status="blocked")

    @staticmethod
    def _clip(value: str, limit: int = 1_000) -> str:
        value = value.strip()
        return value if len(value) <= limit else value[:limit] + "…"

    @staticmethod
    def _usage_summary(result: Any) -> dict[str, Any]:
        usage = getattr(result, "usage", None)
        usage = usage() if callable(usage) else usage
        if usage is None:
            return {}
        return {
            name: getattr(usage, name, None)
            for name in ("requests", "tool_calls", "input_tokens", "output_tokens")
            if getattr(usage, name, None) is not None
        }
