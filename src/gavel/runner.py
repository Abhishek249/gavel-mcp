from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from gavel.fixtures import make_taxi_trips
from gavel.models import CheckStatus, ValidationReport
from gavel.pipelines import candidate_pipeline, reference_pipeline
from gavel.validators import validate


def run_validation(
    faults: Iterable[str] = (), row_count: int = 1_000, seed: int = 42
) -> ValidationReport:
    normalized_faults = sorted(set(faults))
    source = make_taxi_trips(row_count=row_count, seed=seed)
    checks = validate(
        reference_pipeline(source),
        candidate_pipeline(source, faults=normalized_faults),
    )
    fingerprint = json.dumps(
        {"faults": normalized_faults, "row_count": row_count, "seed": seed}, sort_keys=True
    )
    run_id = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    return ValidationReport(
        run_id=run_id,
        dataset=f"synthetic-nyc-taxi:{row_count}:seed-{seed}",
        candidate_faults=normalized_faults,
        status=CheckStatus.FAIL if any(check.status == CheckStatus.FAIL for check in checks) else CheckStatus.PASS,
        checks=checks,
    )

