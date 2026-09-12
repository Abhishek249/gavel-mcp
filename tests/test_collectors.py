from __future__ import annotations

from unittest.mock import patch

from proofline.collectors.manual_report import collect_manual_report_candidate


@patch("proofline.collectors.manual_report.find_dagster_run_by_manual_report")
@patch("proofline.collectors.manual_report.dagster_materialization_metadata")
@patch("proofline.collectors.manual_report.dagster_run_status")
@patch("proofline.collectors.manual_report.find_wo_job_by_name")
@patch("proofline.collectors.manual_report.fetch_rows")
def test_collect_manual_report_candidate_merges_sources(
    mock_fetch_rows,
    mock_find_wo,
    mock_dagster_status,
    mock_dagster_metadata,
    mock_find_dagster_run,
) -> None:
    manual_report_id = "f6b07a32-ff8b-45b2-a784-cd38ff2d7213"
    mock_fetch_rows.return_value = [
        {
            "manual_report_id": manual_report_id,
            "driving_session_count": 3,
            "gap_count": 1,
            "lisa_count": 0,
            "boundary_result_id": "92f241ca-2b4e-42bd-b48a-d30091462e14",
            "aggregated_fov_wkt": "POLYGON((0 0, 0 50, 50 50, 50 0, 0 0))",
            "aggregated_fov_present": True,
        }
    ]
    mock_find_wo.side_effect = [
        {"status": "SUCCEEDED", "adapter_run_id": "autofov-run"},
        {"status": "SUBMITTED", "adapter_run_id": "lisa-run"},
    ]
    mock_dagster_status.side_effect = ["SUCCESS", "SUCCESS"]
    mock_dagster_metadata.side_effect = [
        {
            "tile_count": 4,
            "postgres_written": True,
            "polygon_generated": True,
        },
        {"gap_count": 1, "postgres_written": True},
    ]
    mock_find_dagster_run.return_value = None

    row = collect_manual_report_candidate(manual_report_id)

    assert row["driving_session_count"] == 3
    assert row["autofov_tile_count"] == 4
    assert row["autofov_postgres_written"] is True
    assert row["autofov_wo_status"] == "SUCCEEDED"
    assert row["lisa_orchestration_status"] == "SUCCESS"
    assert row["collection"]["autofov_adapter_run_id"] == "autofov-run"


@patch("proofline.sandbox.runner.collect_manual_report_candidate")
def test_live_sandbox_validation_uses_collector(mock_collect) -> None:
    from proofline.models import CheckStatus
    from proofline.sandbox.runner import run_sandbox_validation

    manual_report_id = "f6b07a32-ff8b-45b2-a784-cd38ff2d7213"
    mock_collect.return_value = {
        "manual_report_id": manual_report_id,
        "driving_session_count": 3,
        "autofov_tile_count": 4,
        "autofov_postgres_written": True,
        "aggregated_fov_wkt": "POLYGON((0 0, 0 50, 50 50, 50 0, 0 0))",
        "gap_count": 1,
        "lisa_orchestration_status": "SUCCESS",
    }
    report = run_sandbox_validation(
        "manual-report-in1290",
        params={"live": True, "manual_report_id": manual_report_id, "candidate_key": manual_report_id},
    )
    assert report.status == CheckStatus.PASS
    assert report.context["live"] is True
    mock_collect.assert_called_once_with(manual_report_id)


def test_geospatial_accepts_succeeded_worker_status() -> None:
    from proofline.geospatial import GeospatialRunEvidence, validate_geospatial_evidence
    from proofline.models import CheckStatus

    report = validate_geospatial_evidence(
        GeospatialRunEvidence(
            parent_id="mr-1",
            orchestration_status="SUCCESS",
            worker_status="SUCCEEDED",
            tile_count=4,
            polygon_generated=True,
            postgres_written=True,
            result_row_count=1,
            aggregated_shape_present=True,
        )
    )
    assert report.status == CheckStatus.PASS
