from __future__ import annotations

import math
from typing import Any

from shapely import wkt
from shapely.geometry.base import BaseGeometry

from gavel.models import CheckResult, CheckStatus
from gavel.sandbox.spec import MetricSpec


def _resolve_field(side: str, field_ref: str, row: dict[str, Any], row_count: int) -> Any:
    if field_ref == f"{side}.__rows__":
        return row_count
    if field_ref == f"{side}.rows":
        return row_count
    prefix = f"{side}."
    if not field_ref.startswith(prefix):
        raise ValueError(f"field reference must start with '{prefix}': {field_ref}")
    column = field_ref[len(prefix) :]
    if column not in row:
        raise KeyError(f"column '{column}' missing from {side} row")
    return row[column]


def _parse_geometry(value: Any) -> BaseGeometry:
    if value is None:
        raise ValueError("geometry value is null")
    if isinstance(value, BaseGeometry):
        return value
    if not isinstance(value, str):
        raise TypeError(f"expected WKT string or geometry, got {type(value).__name__}")
    geometry = wkt.loads(value)
    if geometry.is_empty:
        raise ValueError("geometry is empty")
    return geometry


def _jaccard(left: BaseGeometry, right: BaseGeometry) -> float:
    if not left.is_valid:
        left = left.buffer(0)
    if not right.is_valid:
        right = right.buffer(0)
    intersection = left.intersection(right).area
    union = left.union(right).area
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    return intersection / union


def _check(
    name: str,
    passed: bool,
    expected: Any,
    actual: Any,
    evidence: dict[str, Any] | None = None,
) -> CheckResult:
    return CheckResult(
        name=name,
        status=CheckStatus.PASS if passed else CheckStatus.FAIL,
        expected=expected,
        actual=actual,
        evidence=evidence or {},
    )


def evaluate_metric(
    metric: MetricSpec,
    *,
    golden_row: dict[str, Any],
    candidate_row: dict[str, Any],
    golden_row_count: int,
    candidate_row_count: int,
) -> CheckResult:
    golden_value = _resolve_field("golden", metric.golden, golden_row, golden_row_count)
    candidate_value = _resolve_field("candidate", metric.candidate, candidate_row, candidate_row_count)

    if metric.fn == "row_count":
        expected = golden_value
        actual = candidate_value
        return _check(metric.name, expected == actual, expected, actual)

    if metric.fn == "not_null":
        return _check(metric.name, candidate_value is not None, "not null", candidate_value)

    if metric.fn == "exact":
        if metric.tolerance is not None and isinstance(golden_value, (int, float)) and isinstance(
            candidate_value, (int, float)
        ):
            if golden_value == 0:
                passed = candidate_value == 0
            else:
                passed = abs(candidate_value - golden_value) / abs(golden_value) <= metric.tolerance
            return _check(
                metric.name,
                passed,
                golden_value,
                candidate_value,
                {"tolerance": metric.tolerance},
            )
        return _check(metric.name, golden_value == candidate_value, golden_value, candidate_value)

    if metric.fn == "gte":
        threshold = metric.threshold
        if threshold is None:
            raise ValueError(f"metric {metric.name} requires threshold")
        passed = candidate_value >= threshold
        return _check(metric.name, passed, f">= {threshold}", candidate_value)

    if metric.fn == "lte":
        threshold = metric.threshold
        if threshold is None:
            raise ValueError(f"metric {metric.name} requires threshold")
        passed = candidate_value <= threshold
        return _check(metric.name, passed, f"<= {threshold}", candidate_value)

    if metric.fn == "jaccard":
        threshold = metric.threshold if metric.threshold is not None else 0.95
        left = _parse_geometry(golden_value)
        right = _parse_geometry(candidate_value)
        score = _jaccard(left, right)
        passed = score >= float(threshold)
        return _check(
            metric.name,
            passed,
            f">= {threshold}",
            round(score, 6),
            {
                "golden_area": round(left.area, 6),
                "candidate_area": round(right.area, 6),
            },
        )

    if metric.fn == "area_ratio":
        tolerance = metric.tolerance if metric.tolerance is not None else 0.05
        left = _parse_geometry(golden_value)
        right = _parse_geometry(candidate_value)
        if left.area == 0:
            delta = 0.0 if right.area == 0 else math.inf
        else:
            delta = abs(right.area - left.area) / left.area
        passed = delta <= tolerance
        return _check(
            metric.name,
            passed,
            f"relative delta <= {tolerance}",
            round(delta, 6),
            {
                "golden_area": round(left.area, 6),
                "candidate_area": round(right.area, 6),
            },
        )

    raise ValueError(f"unsupported metric fn: {metric.fn}")
