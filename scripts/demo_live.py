"""Run a concise, real MCP interaction for terminal recording."""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
VIOLET = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def report_from(response) -> dict:
    assert not response.isError
    assert response.content and hasattr(response.content[0], "text")
    return json.loads(response.content[0].text)


async def pause(message: str, delay: float = 0.7) -> None:
    print(message, flush=True)
    await asyncio.sleep(delay)


async def main() -> None:
    await pause(f"{BOLD}{VIOLET}GAVEL MCP — LIVE VALIDATION{RESET}")
    await pause("Starting MCP server over stdio ...")

    server = StdioServerParameters(command=sys.executable, args=["-m", "gavel.server"])
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        await pause(f"{GREEN}✓ MCP handshake complete{RESET}")

        tools = await session.list_tools()
        names = sorted(tool.name for tool in tools.tools)
        await pause(f"{GREEN}✓ Tools discovered:{RESET} {', '.join(names)}")

        await pause(f"\n{CYAN}1. Validating a clean candidate ...{RESET}")
        clean = report_from(
            await session.call_tool(
                "validate_candidate_pipeline",
                {"faults": [], "row_count": 500, "seed": 42},
            )
        )
        await pause(f"   Decision: {GREEN}{BOLD}{clean['status'].upper()}{RESET}")

        await pause(f"\n{CYAN}2. Injecting a missing partition ...{RESET}")
        broken = report_from(
            await session.call_tool(
                "validate_candidate_pipeline",
                {"faults": ["missing_partition"], "row_count": 500, "seed": 42},
            )
        )
        failures = [
            check["name"] for check in broken["checks"] if check["status"] == "fail"
        ]
        await pause(f"   Decision: {RED}{BOLD}{broken['status'].upper()}{RESET}")
        await pause(f"   Evidence: {', '.join(failures)}")

        await pause(f"\n{CYAN}3. Checking a geospatial silent-success run ...{RESET}")
        geo = report_from(
            await session.call_tool(
                "validate_geospatial_run",
                {
                    "evidence": {
                        "parent_id": "public-demo",
                        "orchestration_status": "SUCCESS",
                        "worker_status": "Completed",
                        "tile_count": 120,
                        "polygon_generated": False,
                        "postgres_written": False,
                        "result_row_count": 0,
                        "aggregated_shape_present": False,
                    }
                },
            )
        )
        geo_failures = [
            check["name"] for check in geo["checks"] if check["status"] == "fail"
        ]
        await pause("   Orchestrator: SUCCESS")
        await pause(f"   Semantic decision: {RED}{BOLD}{geo['status'].upper()}{RESET}")
        await pause(f"   Violations: {', '.join(geo_failures)}")

    await pause(
        f"\\n{GREEN}{BOLD}Proof complete: green jobs are not accepted without evidence.{RESET}",
        1.2,
    )


if __name__ == "__main__":
    asyncio.run(main())
