"""Customer Service agent: careful, unsent customer-message drafts."""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from ..models import AgentDependencies, AgentReport
from .common import build_agent


def build(model: Any) -> Agent[AgentDependencies, AgentReport]:
    return build_agent("customer_service", model)
