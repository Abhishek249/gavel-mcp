from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import timedelta

from gavel.fixtures import Trip

SUPPORTED_FAULTS = {
    "duplicate_rows",
    "missing_partition",
    "timezone_shift",
    "wrong_zone_mapping",
}


@dataclass(frozen=True, slots=True)
class PipelineOutput:
    trips: tuple[Trip, ...]
    fare_by_zone: dict[int, float]


def _aggregate(trips: Iterable[Trip]) -> PipelineOutput:
    materialized = tuple(trips)
    totals: defaultdict[int, float] = defaultdict(float)
    for trip in materialized:
        totals[trip.pickup_zone] += trip.fare_usd
    return PipelineOutput(
        trips=materialized,
        fare_by_zone={zone: round(total, 2) for zone, total in sorted(totals.items())},
    )


def reference_pipeline(trips: Iterable[Trip]) -> PipelineOutput:
    return _aggregate(trips)


def candidate_pipeline(trips: Iterable[Trip], faults: Iterable[str] = ()) -> PipelineOutput:
    requested = set(faults)
    unknown = requested - SUPPORTED_FAULTS
    if unknown:
        raise ValueError(f"Unsupported faults: {', '.join(sorted(unknown))}")

    candidate = list(trips)
    if "missing_partition" in requested:
        candidate = [trip for trip in candidate if trip.pickup_at.day != 15]
    if "timezone_shift" in requested:
        candidate = [replace(trip, pickup_at=trip.pickup_at + timedelta(hours=5, minutes=30)) for trip in candidate]
    if "wrong_zone_mapping" in requested:
        candidate = [replace(trip, pickup_zone=(trip.pickup_zone % 20) + 1) for trip in candidate]
    if "duplicate_rows" in requested:
        candidate.extend(candidate[: max(1, len(candidate) // 20)])

    return _aggregate(candidate)
