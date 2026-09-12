from __future__ import annotations

import pytest

from proofline.models import CheckStatus
from proofline.sandbox.loader import (
    list_sandboxes,
    load_dataset_rows,
    load_sandbox_spec,
    sandbox_dir_for,
)
from proofline.sandbox.runner import run_sandbox_validation


def test_list_sandboxes_discovers_shipped_examples() -> None:
    sandboxes = list_sandboxes()
    names = {entry["name"] for entry in sandboxes}
    assert "q2755-dual-write" in names
    assert "manual-report-in1290" in names


def test_manual_report_in1290_passes_when_candidate_matches_golden() -> None:
    report = run_sandbox_validation(
        "manual-report-in1290",
        params={"candidate_key": "f6b07a32-ff8b-45b2-a784-cd38ff2d7213"},
    )
    assert report.status == CheckStatus.PASS
    assert report.failed_checks == []
    assert report.context["sandbox"] == "manual-report-in1290"
    assert "postgres_qa" in report.context["components"]


def test_manual_report_in1290_fails_when_candidate_drifts() -> None:
    report = run_sandbox_validation(
        "manual-report-in1290",
        params={"candidate_key": "f6b07a32-ff8b-45b2-a784-cd38ff2d7213"},
        candidate_rows=[
            {
                "manual_report_id": "f6b07a32-ff8b-45b2-a784-cd38ff2d7213",
                "driving_session_count": 3,
                "autofov_tile_count": 4,
                "autofov_postgres_written": True,
                "aggregated_fov_wkt": "POLYGON((5 0, 5 50, 50 50, 50 0, 5 0))",
                "gap_count": 2,
                "lisa_orchestration_status": "SUCCESS",
            }
        ],
    )
    assert report.status == CheckStatus.FAIL
    assert "autogaps_gap_count" in report.failed_checks
    assert "aggregated_fov_jaccard" in report.failed_checks


def test_q2755_dual_write_fails_jaccard_on_packaged_candidate() -> None:
    report = run_sandbox_validation(
        "q2755-dual-write",
        params={"candidate_key": "3df9572e-73bf-45e6-86eb-fcc2e30d7ee0"},
    )
    assert report.status == CheckStatus.FAIL
    jaccard = next(check for check in report.checks if check.name == "aggregated_fov_jaccard")
    assert jaccard.status == CheckStatus.FAIL
    assert jaccard.actual == pytest.approx(0.9, rel=1e-3)
    assert "gap_count_exact" not in report.failed_checks


def test_q2755_passes_when_candidate_matches_golden() -> None:
    spec = load_sandbox_spec("q2755-dual-write")
    golden_rows = load_dataset_rows(
        "golden", spec.datasets["golden"], sandbox_dir=sandbox_dir_for("q2755-dual-write")
    )
    report = run_sandbox_validation(
        "q2755-dual-write",
        params={"candidate_key": "3df9572e-73bf-45e6-86eb-fcc2e30d7ee0"},
        candidate_rows=golden_rows,
    )
    assert report.status == CheckStatus.PASS


def test_validate_sandbox_run_mcp_tool() -> None:
    from proofline.server import validate_sandbox_run

    report = validate_sandbox_run(
        sandbox="manual-report-in1290",
        params={"candidate_key": "f6b07a32-ff8b-45b2-a784-cd38ff2d7213"},
    )
    assert report["status"] == "pass"
    assert report["context"]["sandbox"] == "manual-report-in1290"
