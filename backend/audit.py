"""Append-only JSON Lines audit trail for every agent workflow step."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from collections import deque

from .models import AgentRole, AuditEvent, WorkflowState


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_TRAIL_PATH = PROJECT_ROOT / "output" / "audit_trail.json"
_PRIVATE_AUDIT_FIELDS = frozenset(
    {
        "requester",
        "notes",
        "email",
        "phone",
        "address",
        "contact_email",
        "contact_phone",
        "recipient",
        "body",
    }
)


def audit_safe(value: Any) -> Any:
    """Remove direct contact and free-form message fields from audit payloads."""
    if isinstance(value, dict):
        return {
            key: audit_safe(item)
            for key, item in value.items()
            if key.casefold() not in _PRIVATE_AUDIT_FIELDS
        }
    if isinstance(value, list):
        return [audit_safe(item) for item in value]
    if isinstance(value, str) and len(value) > 2_000:
        return value[:2_000] + "…"
    return value


def task_fingerprint(task: str) -> dict[str, int | str]:
    """Identify an audited task without copying its potentially sensitive text."""
    encoded = task.encode("utf-8")
    return {
        "task_sha256": hashlib.sha256(encoded).hexdigest(),
        "task_characters": len(task),
    }


class AuditTrail:
    """Append complete JSON records without truncating prior runs."""

    def __init__(self, path: Path = AUDIT_TRAIL_PATH) -> None:
        self.path = path

    def record(
        self,
        workflow: WorkflowState,
        event_type: str,
        *,
        agent: AgentRole | None = None,
        parent_agent: AgentRole | None = None,
        ticket_id: int | None = None,
        delegation_depth: int | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        event = AuditEvent(
            run_id=workflow.run_id,
            step=workflow.next_step(),
            event_type=event_type,
            agent=agent,
            parent_agent=parent_agent,
            ticket_id=ticket_id,
            delegation_depth=delegation_depth,
            details=audit_safe(details or {}),
        )
        self.append(event)

    def append(self, event: AuditEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (event.model_dump_json() + "\n").encode("utf-8")
        descriptor = os.open(
            self.path,
            os.O_APPEND | os.O_CREAT | os.O_WRONLY,
            0o600,
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            os.fchmod(descriptor, 0o600)
            remaining = memoryview(encoded)
            while remaining:
                written = os.write(descriptor, remaining)
                if written == 0:
                    raise OSError("Audit trail append made no progress")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def recent_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """Read the newest complete JSONL events while coordinating with appenders."""
        if limit <= 0 or not self.path.is_file():
            return []
        descriptor = os.open(self.path, os.O_RDONLY)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH)
            recent: deque[dict[str, Any]] = deque(maxlen=limit)
            with os.fdopen(descriptor, "r", encoding="utf-8", closefd=False) as stream:
                for line in stream:
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(value, dict):
                        recent.append(value)
            return list(recent)
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
