import pytest

from gavel.models import CheckStatus
from gavel.runner import run_validation


def test_clean_pipeline_passes() -> None:
    report = run_validation(row_count=250)
    assert report.status == CheckStatus.PASS
    assert report.failed_checks == []


@pytest.mark.parametrize(
    ("fault", "expected_check"),
    [
        ("duplicate_rows", "key_uniqueness"),
        ("missing_partition", "key_set"),
        ("timezone_shift", "pickup_hour_distribution"),
        ("wrong_zone_mapping", "fare_by_pickup_zone"),
    ],
)
def test_fault_is_detected(fault: str, expected_check: str) -> None:
    report = run_validation(faults=[fault], row_count=500)
    assert report.status == CheckStatus.FAIL
    assert expected_check in report.failed_checks


def test_run_id_is_reproducible() -> None:
    first = run_validation(faults=["duplicate_rows"], row_count=50, seed=7)
    second = run_validation(faults=["duplicate_rows"], row_count=50, seed=7)
    assert first.run_id == second.run_id


def test_unknown_fault_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported faults"):
        run_validation(faults=["invented_fault"])

