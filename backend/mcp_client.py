"""stdio client for the one approved source of Campus Customs shop facts."""

from __future__ import annotations

import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER_PATH = PROJECT_ROOT / "mcp_server" / "server.py"
ALLOWED_MCP_TOOLS = frozenset(
    {
        "get_customer_order_context",
        "get_rent_ticket_context",
        "get_discount_request_context",
        "list_open_tickets",
        "get_inventory_for_sku",
        "list_vendor_capabilities",
        "assess_invoice_payment",
        "assess_lease_payment",
        "list_tickets",
        "get_cash_balance",
        "list_purchase_orders",
        "approve_payment",
        "approve_purchase_order",
        "reset_working_database",
    }
)


class MCPToolError(RuntimeError):
    """Raised when the configured Campus Customs MCP server cannot answer."""


class CampusCustomsMCPClient:
    """Own one MCP stdio session; all product/account facts come through it."""

    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> CampusCustomsMCPClient:
        if not MCP_SERVER_PATH.is_file():
            raise FileNotFoundError(f"MCP server file is missing: {MCP_SERVER_PATH}")
        stack = AsyncExitStack()
        await stack.__aenter__()
        try:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=[str(MCP_SERVER_PATH)],
                cwd=str(PROJECT_ROOT),
            )
            read_stream, write_stream = await stack.enter_async_context(
                stdio_client(parameters)
            )
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
            exposed = {tool.name for tool in (await session.list_tools()).tools}
            missing = sorted(ALLOWED_MCP_TOOLS - exposed)
            if missing:
                raise MCPToolError(
                    "MCP server is missing required backend tools: " + ", ".join(missing)
                )
            self._stack = stack
            self._session = session
            return self
        except Exception:
            await stack.aclose()
            raise

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._stack is not None:
            await self._stack.__aexit__(exc_type, exc, traceback)
        self._session = None
        self._stack = None

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in ALLOWED_MCP_TOOLS:
            raise MCPToolError(f"Tool {name!r} is not on the backend MCP allowlist.")
        if self._session is None:
            raise MCPToolError("MCP session is not open.")
        result = await self._session.call_tool(name, arguments)
        if result.isError:
            error_parts = [
                item.text for item in result.content if getattr(item, "text", None)
            ]
            message = " ".join(error_parts).strip()[:500]
            raise MCPToolError(message or f"MCP tool {name!r} returned an error.")
        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, dict):
            return structured
        text_parts = [
            item.text for item in result.content if getattr(item, "text", None)
        ]
        if text_parts:
            try:
                parsed = json.loads("\n".join(text_parts))
            except json.JSONDecodeError as exc:
                raise MCPToolError(
                    f"MCP tool {name!r} returned non-JSON text."
                ) from exc
            if isinstance(parsed, dict):
                return parsed
        raise MCPToolError(f"MCP tool {name!r} returned no structured data.")
