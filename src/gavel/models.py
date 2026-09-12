from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class CheckResult(BaseModel):
    name: str
    status: CheckStatus
    expected: Any
    actual: Any
    evidence: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    run_id: str
    dataset: str
    candidate_faults: list[str]
    status: CheckStatus
    checks: list[CheckResult]
    context: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def failed_checks(self) -> list[str]:
        return [check.name for check in self.checks if check.status == CheckStatus.FAIL]
