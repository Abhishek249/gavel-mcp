from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from proofline.collectors.manual_report import collect_manual_report_candidate
from proofline.models import CheckResult, CheckStatus, ValidationReport
from proofline.sandbox.loader import load_dataset_rows, load_sandbox_spec, sandbox_dir_for
from proofline.sandbox.metrics import evaluate_metric
from proofline.sandbox.spec import SandboxSpec


def _maybe_collect_live_candidate(
    sandbox_name: str,
    params: dict[str, Any],
    candidate_rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if candidate_rows is not None:
        return candidate_rows
    if not params.get("live"):
        return None
    manual_report_id = params.get("manual_report_id") or params.get("candidate_key")
    if sandbox_name == "manual-report-in1290" and manual_report_id:
        return [collect_manual_report_candidate(str(manual_report_id))]
    raise ValueError(
        "params.live=true requires a supported collector; "
        "manual-report-in1290 needs params.manual_report_id or params.candidate_key"
    )


def _select_row(
    rows: list[dict[str, Any]],
    *,
    key: str | None,
    key_value: Any | None,
    dataset_name: str,
) -> dict[str, Any]:
    if not rows:
        raise ValueError(f"{dataset_name} dataset is empty")

    if key_value is not None and key:
        matches = [row for row in rows if row.get(key) == key_value]
        if not matches:
            raise ValueError(
                f"{dataset_name} dataset has no row where {key}={key_value!r}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"{dataset_name} dataset matched multiple rows for {key}={key_value!r}"
            )
        return matches[0]

    if len(rows) != 1:
        raise ValueError(
            f"{dataset_name} dataset has {len(rows)} rows; provide align key via params"
        )
    return rows[0]


def _align_rows(
    spec: SandboxSpec,
    golden_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    params: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    evidence: dict[str, Any] = {
        "golden_row_count": len(golden_rows),
        "candidate_row_count": len(candidate_rows),
    }

    if spec.align:
        golden_key_value = params.get("golden_key")
        candidate_key_value = params.get("candidate_key", golden_key_value)
        if candidate_key_value is None:
            raise ValueError("params.candidate_key or params.golden_key required for aligned sandboxes")
        golden_row = _select_row(
            golden_rows,
            key=spec.align.golden_key,
            key_value=golden_key_value,
            dataset_name="golden",
        )
        candidate_row = _select_row(
            candidate_rows,
            key=spec.align.candidate_key,
            key_value=candidate_key_value,
            dataset_name="candidate",
        )
        evidence["golden_key"] = {spec.align.golden_key: golden_row.get(spec.align.golden_key)}
        evidence["candidate_key"] = {spec.align.candidate_key: candidate_row.get(spec.align.candidate_key)}
        return golden_row, candidate_row, evidence

    golden_key = spec.datasets["golden"].key
    candidate_key = spec.datasets["candidate"].key
    key_value = params.get("key") or params.get("golden_key") or params.get("candidate_key")
    if key_value is not None and golden_key and candidate_key:
        golden_row = _select_row(golden_rows, key=golden_key, key_value=key_value, dataset_name="golden")
        candidate_row = _select_row(
            candidate_rows, key=candidate_key, key_value=key_value, dataset_name="candidate"
        )
        evidence["key"] = key_value
        return golden_row, candidate_row, evidence

    return (
        _select_row(golden_rows, key=None, key_value=None, dataset_name="golden"),
        _select_row(candidate_rows, key=None, key_value=None, dataset_name="candidate"),
        evidence,
    )


def run_sandbox_validation(
    sandbox_name: str,
    *,
    params: dict[str, Any] | None = None,
    candidate_rows: list[dict[str, Any]] | None = None,
    candidate_path: str | Path | None = None,
    sandbox_root: Path | None = None,
) -> ValidationReport:
    """Evaluate all sandbox metrics for golden vs candidate datasets."""
    params = dict(params or {})
    spec = load_sandbox_spec(sandbox_name, root=sandbox_root)
    sandbox_dir = sandbox_dir_for(sandbox_name, root=sandbox_root)

    golden_rows = load_dataset_rows("golden", spec.datasets["golden"], sandbox_dir=sandbox_dir)
    candidate_file = Path(candidate_path) if candidate_path else None
    live_candidate_rows = _maybe_collect_live_candidate(sandbox_name, params, candidate_rows)
    candidate_dataset_rows = load_dataset_rows(
        "candidate",
        spec.datasets["candidate"],
        sandbox_dir=sandbox_dir,
        inline_override=live_candidate_rows if live_candidate_rows is not None else candidate_rows,
        file_override=candidate_file,
    )

    golden_row, candidate_row, align_evidence = _align_rows(
        spec, golden_rows, candidate_dataset_rows, params
    )

    checks: list[CheckResult] = []
    for metric in spec.metrics:
        checks.append(
            evaluate_metric(
                metric,
                golden_row=golden_row,
                candidate_row=candidate_row,
                golden_row_count=len(golden_rows),
                candidate_row_count=len(candidate_dataset_rows),
            )
        )

    fingerprint = json.dumps(
        {
            "sandbox": sandbox_name,
            "params": params,
            "candidate_path": str(candidate_path) if candidate_path else None,
            "candidate_rows": candidate_rows,
        },
        sort_keys=True,
        default=str,
    )
    run_id = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    status = (
        CheckStatus.FAIL
        if any(check.status == CheckStatus.FAIL for check in checks)
        else CheckStatus.PASS
    )
    return ValidationReport(
        run_id=run_id,
        dataset=f"sandbox:{sandbox_name}",
        candidate_faults=[],
        status=status,
        checks=checks,
        context={
            "sandbox": sandbox_name,
            "sandbox_version": spec.version,
            "components": list(spec.components.keys()),
            "alignment": align_evidence,
            "live": bool(params.get("live")),
        },
    )
