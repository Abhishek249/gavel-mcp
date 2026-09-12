from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from proofline.models import CheckResult, CheckStatus, ValidationReport


class GeospatialRunEvidence(BaseModel):
    """Facts collected from an orchestrated geospatial pipeline run."""

    parent_id: str = Field(min_length=1, description="Opaque parent/job identifier")
    run_id: str | None = Field(default=None, description="Optional orchestrator run identifier")
    orchestration_status: str
    worker_status: str
    tile_count: int = Field(ge=0)
    polygon_generated: bool
    postgres_written: bool
    result_row_count: int = Field(ge=0)
    aggregated_shape_present: bool
    expected_session_count: int | None = Field(default=None, ge=0)
    actual_session_count: int | None = Field(default=None, ge=0)
    reference_area: float | None = Field(default=None, gt=0)
    candidate_area: float | None = Field(default=None, ge=0)
    jaccard_index: float | None = Field(default=None, ge=0, le=1)
    minimum_jaccard: float = Field(default=0.95, ge=0, le=1)
    area_tolerance_ratio: float = Field(default=0.05, ge=0, le=1)


def _check(
    name: str,
    passed: bool,
    expected: Any,
    actual: Any,
    evidence: dict[str, Any] | None = None,
) -> CheckResult:
    return CheckResult(
        name=name,
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        expected=expected,
        actual=actual,
        evidence=evidence or {},
    )


def validate_geospatial_evidence(evidence: GeospatialRunEvidence) -> ValidationReport:
    """Evaluate cross-system invariants without requiring access to private infrastructure."""
    checks = [
        _check(
            "orchestration_succeeded",
            evidence.orchestration_status.upper() == "SUCCESS",
            "SUCCESS",
            evidence.orchestration_status,
        ),
        _check(
            "worker_completed",
            evidence.worker_status.upper() in {"COMPLETED", "SUCCEEDED", "SUCCESS"},
            "COMPLETED|SUCCEEDED",
            evidence.worker_status,
        ),
        _check(
            "result_row_exists",
            evidence.result_row_count > 0,
            "at least 1",
            evidence.result_row_count,
        ),
        _check(
            "polygon_generated_when_tiles_exist",
            evidence.tile_count == 0 or evidence.polygon_generated,
            True,
            evidence.polygon_generated,
            {"tile_count": evidence.tile_count},
        ),
        _check(
            "postgres_written_when_polygon_generated",
            not evidence.polygon_generated or evidence.postgres_written,
            True,
            evidence.postgres_written,
            {"polygon_generated": evidence.polygon_generated},
        ),
        _check(
            "aggregated_shape_present_when_tiles_exist",
            evidence.tile_count == 0 or evidence.aggregated_shape_present,
            True,
            evidence.aggregated_shape_present,
            {"tile_count": evidence.tile_count},
        ),
    ]

    if evidence.expected_session_count is not None:
        checks.append(
            _check(
                "session_count_matches",
                evidence.actual_session_count == evidence.expected_session_count,
                evidence.expected_session_count,
                evidence.actual_session_count,
            )
        )

    if evidence.jaccard_index is not None:
        checks.append(
            _check(
                "jaccard_meets_threshold",
                evidence.jaccard_index >= evidence.minimum_jaccard,
                f">= {evidence.minimum_jaccard}",
                evidence.jaccard_index,
            )
        )

    if evidence.reference_area is not None:
        area_delta = (
            None
            if evidence.candidate_area is None
            else abs(evidence.candidate_area - evidence.reference_area) / evidence.reference_area
        )
        checks.append(
            _check(
                "area_within_tolerance",
                area_delta is not None and area_delta <= evidence.area_tolerance_ratio,
                f"relative delta <= {evidence.area_tolerance_ratio}",
                area_delta,
                {
                    "reference_area": evidence.reference_area,
                    "candidate_area": evidence.candidate_area,
                },
            )
        )

    fingerprint = json.dumps(evidence.model_dump(mode="json"), sort_keys=True)
    run_id = evidence.run_id or hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    status = (
        CheckStatus.FAIL
        if any(check.status == CheckStatus.FAIL for check in checks)
        else CheckStatus.PASS
    )
    return ValidationReport(
        run_id=run_id,
        dataset=f"geospatial-run:{evidence.parent_id}",
        candidate_faults=[],
        status=status,
        checks=checks,
    )
