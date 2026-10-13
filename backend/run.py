"""Read-only command-line entry point for a board or single-ticket team run."""

from __future__ import annotations

import argparse
import asyncio

from .mcp_client import CampusCustomsMCPClient
from .team import AgentTeam


async def _run(ticket_id: int | None) -> None:
    async with CampusCustomsMCPClient() as mcp_client:
        team = AgentTeam(mcp_client)
        result = (
            await team.run_ticket(ticket_id)
            if ticket_id is not None
            else await team.run_open_board()
        )
    print(result.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run read-only Campus Customs agent triage through the MCP server."
    )
    parser.add_argument(
        "--ticket-id",
        type=int,
        help="Run the Boss-led workflow for one ticket; omit to review the open board.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.ticket_id))


if __name__ == "__main__":
    main()
