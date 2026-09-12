from gavel.geospatial import GeospatialRunEvidence, validate_geospatial_evidence
from gavel.models import CheckStatus


def healthy_evidence(**overrides) -> GeospatialRunEvidence:
    values = {
        "parent_id": "fixture-1290",
        "run_id": "run-123",
        "orchestration_status": "SUCCESS",
        "worker_status": "Completed",
        "tile_count": 120,
        "polygon_generated": True,
        "postgres_written": True,
        "result_row_count": 1,
        "aggregated_shape_present": True,
        "expected_session_count": 12,
        "actual_session_count": 12,
        "reference_area": 100.0,
        "candidate_area": 98.0,
        "jaccard_index": 0.97,
    }
    values.update(overrides)
    return GeospatialRunEvidence(**values)


def test_healthy_geospatial_run_passes() -> None:
    report = validate_geospatial_evidence(healthy_evidence())
    assert report.status == CheckStatus.PASS
    assert report.failed_checks == []


def test_silent_success_is_detected() -> None:
    report = validate_geospatial_evidence(
        healthy_evidence(
            polygon_generated=False,
            postgres_written=False,
            result_row_count=0,
            aggregated_shape_present=False,
        )
    )
    assert report.status == CheckStatus.FAIL
    assert {
        "result_row_exists",
        "polygon_generated_when_tiles_exist",
        "aggregated_shape_present_when_tiles_exist",
    } <= set(report.failed_checks)


def test_reference_drift_is_detected() -> None:
    report = validate_geospatial_evidence(
        healthy_evidence(
            actual_session_count=10,
            candidate_area=70.0,
            jaccard_index=0.80,
        )
    )
    assert {
        "session_count_matches",
        "jaccard_meets_threshold",
        "area_within_tolerance",
    } <= set(report.failed_checks)


def test_empty_source_does_not_require_polygon() -> None:
    report = validate_geospatial_evidence(
        healthy_evidence(
            tile_count=0,
            polygon_generated=False,
            postgres_written=False,
            aggregated_shape_present=False,
            reference_area=None,
            candidate_area=None,
            jaccard_index=None,
        )
    )
    assert "polygon_generated_when_tiles_exist" not in report.failed_checks
    assert "aggregated_shape_present_when_tiles_exist" not in report.failed_checks
