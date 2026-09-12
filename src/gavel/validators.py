from __future__ import annotations

from collections import Counter
from typing import Any

from gavel.models import CheckResult, CheckStatus
from gavel.pipelines import PipelineOutput


def _check(name: str, expected: Any, actual: Any, evidence: dict[str, Any]) -> CheckResult:
    return CheckResult(
        name=name,
        status=CheckStatus.PASS if expected == actual else CheckStatus.FAIL,
        expected=expected,
        actual=actual,
        evidence=evidence,
    )


def validate(reference: PipelineOutput, candidate: PipelineOutput) -> list[CheckResult]:
    reference_ids = [trip.trip_id for trip in reference.trips]
    candidate_ids = [trip.trip_id for trip in candidate.trips]
    duplicate_ids = sorted(key for key, count in Counter(candidate_ids).items() if count > 1)
    missing_ids = sorted(set(reference_ids) - set(candidate_ids))
    unexpected_ids = sorted(set(candidate_ids) - set(reference_ids))

    reference_hours = Counter(trip.pickup_at.hour for trip in reference.trips)
    candidate_hours = Counter(trip.pickup_at.hour for trip in candidate.trips)

    return [
        _check(
            "row_count",
            len(reference.trips),
            len(candidate.trips),
            {"difference": len(candidate.trips) - len(reference.trips)},
        ),
        _check(
            "key_set",
            True,
            not missing_ids and not unexpected_ids,
            {"missing_sample": missing_ids[:10], "unexpected_sample": unexpected_ids[:10]},
        ),
        _check(
            "key_uniqueness",
            0,
            len(duplicate_ids),
            {"duplicate_sample": duplicate_ids[:10]},
        ),
        _check(
            "fare_by_pickup_zone",
            reference.fare_by_zone,
            candidate.fare_by_zone,
            {
                "mismatched_zones": sorted(
                    zone
                    for zone in set(reference.fare_by_zone) | set(candidate.fare_by_zone)
                    if reference.fare_by_zone.get(zone) != candidate.fare_by_zone.get(zone)
                )
            },
        ),
        _check(
            "pickup_hour_distribution",
            dict(sorted(reference_hours.items())),
            dict(sorted(candidate_hours.items())),
            {"metric": "UTC pickup-hour histogram"},
        ),
    ]

