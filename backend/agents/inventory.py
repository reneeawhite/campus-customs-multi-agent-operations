"""Inventory agent: exact-size stock, shortages, vendors, and lead times."""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent

from ..models import AgentDependencies, AgentReport
from .common import build_agent


def build(model: Any) -> Agent[AgentDependencies, AgentReport]:
    return build_agent("inventory", model)
