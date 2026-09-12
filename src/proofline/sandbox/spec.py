from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ComponentSpec(BaseModel):
    """Declared infrastructure component in the evaluation sandbox."""

    type: Literal["postgres", "sqlserver", "dagster", "wo", "s3", "file"]
    description: str | None = None


class DatasetSpec(BaseModel):
    """How to materialize a tabular dataset for comparison."""

    source: Literal["file", "inline"] = "file"
    path: str | None = None
    rows: list[dict[str, Any]] | None = None
    key: str | None = Field(
        default=None,
        description="Primary key column used to align golden and candidate rows",
    )


class AlignSpec(BaseModel):
    golden_key: str
    candidate_key: str


class MetricSpec(BaseModel):
    name: str
    golden: str = Field(description="Field reference: golden.<column>")
    candidate: str = Field(description="Field reference: candidate.<column>")
    fn: Literal["exact", "jaccard", "area_ratio", "row_count", "not_null", "gte", "lte"]
    threshold: float | int | str | None = None
    tolerance: float | None = Field(
        default=None,
        description="Relative tolerance for exact numeric comparisons",
    )

    @model_validator(mode="after")
    def validate_field_refs(self) -> MetricSpec:
        for ref_name, ref in (("golden", self.golden), ("candidate", self.candidate)):
            prefix = f"{ref_name}."
            if self.fn == "row_count":
                if ref not in {f"{ref_name}.rows", f"{ref_name}.__rows__"}:
                    raise ValueError(
                        f"{ref_name} metric row_count must reference {ref_name}.rows or "
                        f"{ref_name}.__rows__"
                    )
                continue
            if not ref.startswith(prefix):
                raise ValueError(f"{ref_name} must start with '{prefix}'")
        return self


class SandboxSpec(BaseModel):
    name: str
    version: str = "1"
    description: str | None = None
    components: dict[str, ComponentSpec] = Field(default_factory=dict)
    datasets: dict[str, DatasetSpec]
    align: AlignSpec | None = None
    metrics: list[MetricSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def require_golden_and_candidate(self) -> SandboxSpec:
        if "golden" not in self.datasets:
            raise ValueError("sandbox must declare datasets.golden")
        if "candidate" not in self.datasets:
            raise ValueError("sandbox must declare datasets.candidate")
        return self
