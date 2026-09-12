from __future__ import annotations

from typing import Any

from gavel.adapters.http_clients import (
    dagster_materialization_metadata,
    dagster_run_status,
    find_dagster_run_by_manual_report,
    find_wo_job_by_name,
)
from gavel.adapters.postgres import fetch_rows

MANUAL_REPORT_SQL = """
SELECT
  mr.id::text AS manual_report_id,
  (
    SELECT COUNT(*)
    FROM manual_report_driving_session_mapping mapping
    WHERE mapping.manual_report_id = mr.id
  ) AS driving_session_count,
  mr.gap_count,
  mr.lisa_count,
  br.id::text AS boundary_result_id,
  ST_AsText(br.aggregated_fov_shape) AS aggregated_fov_wkt,
  (br.aggregated_fov_shape IS NOT NULL) AS aggregated_fov_present
FROM manual_report mr
LEFT JOIN boundary_result br ON br.manual_report_id = mr.id
WHERE mr.id = %(manual_report_id)s::uuid
"""


def collect_manual_report_candidate(
    manual_report_id: str,
    *,
    wo_url: str | None = None,
    dagster_url: str | None = None,
) -> dict[str, Any]:
    """Collect a candidate evidence row for manual-report sandbox validation."""
    rows = fetch_rows(MANUAL_REPORT_SQL, {"manual_report_id": manual_report_id})
    if not rows:
        raise RuntimeError(f"manual_report not found: {manual_report_id}")

    row = dict(rows[0])
    row["manual_report_id"] = manual_report_id

    autofov_job = find_wo_job_by_name(f"autofov-{manual_report_id}", url=wo_url)
    lisa_job = find_wo_job_by_name(f"lisa-{manual_report_id}", url=wo_url)

    autofov_wo_status = autofov_job.get("status") if autofov_job else None
    lisa_wo_status = lisa_job.get("status") if lisa_job else None
    row["autofov_wo_status"] = autofov_wo_status
    row["lisa_wo_status"] = lisa_wo_status

    autofov_run_id = (autofov_job or {}).get("adapter_run_id")
    lisa_run_id = (lisa_job or {}).get("adapter_run_id")

    autofov_meta: dict[str, Any] = {}
    if autofov_run_id:
        row["autofov_dagster_status"] = dagster_run_status(autofov_run_id, url=dagster_url)
        autofov_meta = dagster_materialization_metadata(autofov_run_id, url=dagster_url)
        row["autofov_tile_count"] = autofov_meta.get("tile_count")
        row["autofov_postgres_written"] = autofov_meta.get("postgres_written")
        row["autofov_polygon_generated"] = autofov_meta.get("polygon_generated")
    else:
        autofov_run = find_dagster_run_by_manual_report(
            manual_report_id,
            "boundary_fov_aggregation_job",
            url=dagster_url,
        )
        if autofov_run:
            autofov_run_id = autofov_run["runId"]
            row["autofov_dagster_status"] = autofov_run.get("status")
            autofov_meta = dagster_materialization_metadata(autofov_run_id, url=dagster_url)
            row["autofov_tile_count"] = autofov_meta.get("tile_count")
            row["autofov_postgres_written"] = autofov_meta.get("postgres_written")
            row["autofov_polygon_generated"] = autofov_meta.get("polygon_generated")

    gaps_run = find_dagster_run_by_manual_report(
        manual_report_id,
        "compute_gaps_job",
        url=dagster_url,
    )
    if gaps_run:
        gaps_meta = dagster_materialization_metadata(gaps_run["runId"], url=dagster_url)
        row["autogaps_dagster_status"] = gaps_run.get("status")
        if gaps_meta.get("gap_count") is not None:
            row["gap_count"] = gaps_meta.get("gap_count")
        row["autogaps_postgres_written"] = gaps_meta.get("postgres_written")
    else:
        row["autogaps_dagster_status"] = None

    if lisa_run_id:
        row["lisa_orchestration_status"] = dagster_run_status(lisa_run_id, url=dagster_url)
    else:
        lisa_run = find_dagster_run_by_manual_report(
            manual_report_id,
            "lisa_aggregation_job",
            url=dagster_url,
        )
        row["lisa_orchestration_status"] = (lisa_run or {}).get("status")

    row["collection"] = {
        "autofov_adapter_run_id": autofov_run_id,
        "lisa_adapter_run_id": lisa_run_id,
        "autofov_metadata_keys": sorted(autofov_meta.keys()),
    }
    return row
