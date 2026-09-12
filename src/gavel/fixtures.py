from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class Trip:
    trip_id: str
    pickup_at: datetime
    dropoff_at: datetime
    pickup_zone: int
    dropoff_zone: int
    distance_miles: float
    fare_usd: float


def make_taxi_trips(row_count: int = 1_000, seed: int = 42) -> list[Trip]:
    """Create a deterministic TLC-shaped dataset suitable for tests and demos."""
    if row_count < 1:
        raise ValueError("row_count must be positive")

    rng = random.Random(seed)
    origin = datetime(2025, 1, 1, tzinfo=UTC)
    trips: list[Trip] = []
    for index in range(row_count):
        pickup = origin + timedelta(minutes=rng.randint(0, 31 * 24 * 60 - 1))
        duration = rng.randint(3, 75)
        distance = round(rng.uniform(0.4, 24.0), 2)
        fare = round(3.0 + distance * rng.uniform(2.2, 3.8), 2)
        trips.append(
            Trip(
                trip_id=f"trip-{index:07d}",
                pickup_at=pickup,
                dropoff_at=pickup + timedelta(minutes=duration),
                pickup_zone=rng.randint(1, 20),
                dropoff_zone=rng.randint(1, 20),
                distance_miles=distance,
                fare_usd=fare,
            )
        )
    return trips
