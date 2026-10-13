"""Five clearly separated Campus Customs agent roles."""

from __future__ import annotations

from typing import Any

from .accounting import build as build_accounting
from .boss import build as build_boss
from .customer_service import build as build_customer_service
from .facilities import build as build_facilities
from .inventory import build as build_inventory


def build_agents(model: Any) -> dict[str, Any]:
    """Build all five roles with the same configured Portkey model."""
    return {
        "boss": build_boss(model),
        "inventory": build_inventory(model),
        "accounting": build_accounting(model),
        "facilities": build_facilities(model),
        "customer_service": build_customer_service(model),
    }
