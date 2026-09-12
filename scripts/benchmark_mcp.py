"""Benchmark Proofline through the real MCP protocol boundary."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

FAULTS = {
    "duplicate_rows": {"key_uniqueness"},
    "missing_partition": {"key_set"},
    "timezone_shift": {"pickup_hour_distribution"},
    "wrong_zone_mapping": {"fare_by_pickup_zone"},
}
SEEDS = (7, 42, 99, 2026)
ROW_COUNTS = (100, 500)


def parse_report(response) -> dict:
    assert not response.isError
    assert response.content and hasattr(response.content[0], "text")
    return json.loads(response.content[0].text)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


async def benchmark() -> dict:
    server = StdioServerParameters(command=sys.executable, args=["-m", "proofline.server"])
    results: list[dict] = []
    latencies: list[float] = []

    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        tool_names = sorted(tool.name for tool in tools.tools)
        required_tools = {
            "validate_candidate_pipeline",
            "validate_geospatial_run",
            "list_sandbox_definitions",
            "validate_sandbox_run",
            "collect_manual_report_candidate_row",
            "validate_manual_report_live",
        }
        assert required_tools <= set(tool_names)

        for row_count in ROW_COUNTS:
            for seed in SEEDS:
                for scenario, faults, required_checks in [
                    ("clean", [], set()),
                    *[(name, [name], checks) for name, checks in FAULTS.items()],
                ]:
                    started = time.perf_counter()
                    response = await session.call_tool(
                        "validate_candidate_pipeline",
                        {"faults": faults, "row_count": row_count, "seed": seed},
                    )
                    latency_ms = (time.perf_counter() - started) * 1000
                    report = parse_report(response)
                    failed_checks = {
                        check["name"]
                        for check in report["checks"]
                        if check["status"] == "fail"
                    }
                    defect_present = bool(faults)
                    defect_detected = report["status"] == "fail"
                    diagnostic_correct = required_checks <= failed_checks
                    latencies.append(latency_ms)
                    results.append(
                        {
                            "scenario": scenario,
                            "seed": seed,
                            "row_count": row_count,
                            "defect_present": defect_present,
                            "defect_detected": defect_detected,
                            "diagnostic_correct": diagnostic_correct,
                            "latency_ms": round(latency_ms, 3),
                        }
                    )

    true_positive = sum(r["defect_present"] and r["defect_detected"] for r in results)
    false_negative = sum(r["defect_present"] and not r["defect_detected"] for r in results)
    true_negative = sum(not r["defect_present"] and not r["defect_detected"] for r in results)
    false_positive = sum(not r["defect_present"] and r["defect_detected"] for r in results)
    positive_count = true_positive + false_negative
    negative_count = true_negative + false_positive
    diagnostic_hits = sum(
        r["diagnostic_correct"] for r in results if r["defect_present"]
    )

    metrics = {
        "trials": len(results),
        "defect_trials": positive_count,
        "clean_trials": negative_count,
        "true_positives": true_positive,
        "false_negatives": false_negative,
        "true_negatives": true_negative,
        "false_positives": false_positive,
        "detection_recall": true_positive / positive_count,
        "false_positive_rate": false_positive / negative_count,
        "diagnostic_accuracy": diagnostic_hits / positive_count,
        "latency_ms_p50": round(statistics.median(latencies), 3),
        "latency_ms_p95": round(percentile(latencies, 0.95), 3),
    }
    passed = (
        metrics["detection_recall"] == 1.0
        and metrics["false_positive_rate"] == 0.0
        and metrics["diagnostic_accuracy"] == 1.0
    )
    return {
        "proof": "PASS" if passed else "FAIL",
        "boundary": "MCP stdio client -> Proofline server -> validation engine",
        "tools_discovered": tool_names,
        "matrix": {"seeds": list(SEEDS), "row_counts": list(ROW_COUNTS)},
        "metrics": metrics,
        "results": results,
    }


def markdown_summary(report: dict) -> str:
    metrics = report["metrics"]
    return f"""# Proofline MCP benchmark

**Result: {report["proof"]}**

| Metric | Result |
|---|---:|
| MCP trials | {metrics["trials"]} |
| Detection recall | {metrics["detection_recall"]:.1%} |
| False-positive rate | {metrics["false_positive_rate"]:.1%} |
| Diagnostic accuracy | {metrics["diagnostic_accuracy"]:.1%} |
| Latency p50 | {metrics["latency_ms_p50"]:.3f} ms |
| Latency p95 | {metrics["latency_ms_p95"]:.3f} ms |

The benchmark uses controlled synthetic defects. These figures demonstrate
regression-detection behavior on the published test matrix, not production performance.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    report = asyncio.run(benchmark())
    serialized = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(markdown_summary(report), encoding="utf-8")
    print(serialized, end="")
    if report["proof"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
