from __future__ import annotations

from gavel.models import CheckStatus
from gavel.sandbox.loader import list_sandboxes
from gavel.sandbox.runner import run_sandbox_validation


def test_list_sandboxes_discovers_shipped_examples() -> None:
    sandboxes = list_sandboxes()
    names = {entry["name"] for entry in sandboxes}
    assert "taxi-clean" in names
    assert "taxi-duplicate-rows" in names


def test_taxi_clean_passes_when_candidate_matches_golden() -> None:
    report = run_sandbox_validation("taxi-clean")
    assert report.status == CheckStatus.PASS
    assert report.failed_checks == []
    assert report.context["sandbox"] == "taxi-clean"
    assert "data_warehouse" in report.context["components"]


def test_taxi_duplicate_rows_fails_on_duplicates() -> None:
    report = run_sandbox_validation("taxi-duplicate-rows")
    assert report.status == CheckStatus.FAIL
    assert "row_count" in report.failed_checks or "key_uniqueness" in report.failed_checks


def test_validate_sandbox_run_mcp_tool() -> None:
    from gavel.server import validate_sandbox_run

    report = validate_sandbox_run(sandbox="taxi-clean")
    assert report["status"] == "pass"
    assert report["context"]["sandbox"] == "taxi-clean"
