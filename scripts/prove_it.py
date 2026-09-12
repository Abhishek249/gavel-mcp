"""Exercise Gavel through its public MCP boundary and verify known outcomes."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SCENARIOS = {
    "clean": ([], "pass", set()),
    "duplicate_rows": (["duplicate_rows"], "fail", {"key_uniqueness"}),
    "missing_partition": (["missing_partition"], "fail", {"key_set"}),
    "timezone_shift": (["timezone_shift"], "fail", {"pickup_hour_distribution"}),
    "wrong_zone_mapping": (["wrong_zone_mapping"], "fail", {"fare_by_pickup_zone"}),
}


async def prove() -> dict:
    server = StdioServerParameters(command=sys.executable, args=["-m", "gavel.server"])
    observed: list[dict] = []

    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        tool_names = {tool.name for tool in tools.tools}
        assert {
            "validate_candidate_pipeline",
            "validate_geospatial_run",
            "list_sandbox_definitions",
            "validate_sandbox_run",
            "collect_manual_report_candidate_row",
            "validate_manual_report_live",
        } <= tool_names

        for name, (faults, expected_status, required_failures) in SCENARIOS.items():
            response = await session.call_tool(
                "validate_candidate_pipeline",
                {"faults": faults, "row_count": 500, "seed": 42},
            )
            assert not response.isError
            assert response.content and hasattr(response.content[0], "text")
            report = json.loads(response.content[0].text)
            failed_checks = {
                check["name"] for check in report["checks"] if check["status"] == "fail"
            }
            assert report["status"] == expected_status
            assert required_failures <= failed_checks
            observed.append(
                {
                    "scenario": name,
                    "expected": expected_status,
                    "actual": report["status"],
                    "failed_checks": sorted(failed_checks),
                    "run_id": report["run_id"],
                }
            )

        response = await session.call_tool(
            "validate_geospatial_run",
            {
                "evidence": {
                    "parent_id": "fixture-silent-success",
                    "run_id": "run-silent-success",
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
        assert not response.isError
        assert response.content and hasattr(response.content[0], "text")
        report = json.loads(response.content[0].text)
        failed_checks = {
            check["name"] for check in report["checks"] if check["status"] == "fail"
        }
        required = {
            "result_row_exists",
            "polygon_generated_when_tiles_exist",
            "aggregated_shape_present_when_tiles_exist",
        }
        assert report["status"] == "fail"
        assert required <= failed_checks
        observed.append(
            {
                "scenario": "geospatial_silent_success",
                "expected": "fail",
                "actual": report["status"],
                "failed_checks": sorted(failed_checks),
                "run_id": report["run_id"],
            }
        )

        response = await session.call_tool(
            "validate_sandbox_run",
            {
                "sandbox": "manual-report-in1290",
                "params": {"candidate_key": "f6b07a32-ff8b-45b2-a784-cd38ff2d7213"},
            },
        )
        assert not response.isError
        assert response.content and hasattr(response.content[0], "text")
        report = json.loads(response.content[0].text)
        assert report["status"] == "pass"
        observed.append(
            {
                "scenario": "sandbox_manual_report_in1290",
                "expected": "pass",
                "actual": report["status"],
                "failed_checks": report.get("failed_checks", []),
                "run_id": report["run_id"],
            }
        )

    return {
        "proof": "PASS",
        "boundary": "MCP stdio client -> Gavel MCP server -> validation engine",
        "mcp_tools": sorted(tool_names),
        "scenarios_verified": len(observed),
        "results": observed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    evidence = json.dumps(asyncio.run(prove()), indent=2) + "\n"
    if args.output:
        args.output.write_text(evidence, encoding="utf-8")
    print(evidence, end="")


if __name__ == "__main__":
    main()
