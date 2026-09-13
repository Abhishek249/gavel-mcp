from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from gavel.geospatial import GeospatialRunEvidence, validate_geospatial_evidence
from gavel.runner import run_validation
from gavel.sandbox.loader import list_sandboxes
from gavel.sandbox.runner import run_sandbox_validation

mcp = FastMCP("Gavel", json_response=True)


@mcp.tool()
def validate_candidate_pipeline(
    faults: list[
        Literal["duplicate_rows", "missing_partition", "timezone_shift", "wrong_zone_mapping"]
    ]
    | None = None,
    row_count: int = 1_000,
    seed: int = 42,
) -> dict:
    """Compare a candidate taxi pipeline with a trusted reference and return evidence."""
    return run_validation(faults=faults or [], row_count=row_count, seed=seed).model_dump(mode="json")


@mcp.tool()
def validate_geospatial_run(evidence: GeospatialRunEvidence) -> dict:
    """Validate an orchestrated geospatial run from cross-system evidence.

    Supply facts collected from the orchestrator, worker, database, and optional
    reference comparison. The tool is read-only and never connects to private systems.
    """
    return validate_geospatial_evidence(evidence).model_dump(mode="json")


@mcp.tool()
def list_sandbox_definitions() -> dict:
    """List declarative sandbox eval definitions shipped with Gavel."""
    sandboxes = list_sandboxes()
    return {"count": len(sandboxes), "sandboxes": sandboxes}


@mcp.tool()
def validate_sandbox_run(
    sandbox: str,
    params: dict[str, Any] | None = None,
    candidate_rows: list[dict[str, Any]] | None = None,
    candidate_path: str | None = None,
) -> dict:
    """Evaluate golden vs candidate datasets using a sandbox spec and metric rubric.

    Provide either candidate_rows (inline JSON rows) or candidate_path (JSON file path).
    When the sandbox declares align keys, pass params.golden_key or params.candidate_key.
    """
    report = run_sandbox_validation(
        sandbox,
        params=params,
        candidate_rows=candidate_rows,
        candidate_path=Path(candidate_path) if candidate_path else None,
    )
    return report.model_dump(mode="json")


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
