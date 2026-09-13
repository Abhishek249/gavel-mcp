# Sandbox eval platform

Gavel v0.2 adds a declarative **sandbox eval** layer:

1. **Spec** — declare sandbox components (Postgres, data warehouses, orchestrators, …)
2. **Golden + candidate datasets** — JSON snapshots for deterministic validation
3. **Metrics** — deterministic rubric comparing `golden.col` vs `candidate.col`

Agents invoke validation through MCP:

- `list_sandbox_definitions()`
- `validate_sandbox_run(sandbox, params?, candidate_rows?, candidate_path?)`

## Example: NYC taxi clean data (PASS)

```bash
gavel sandbox taxi-clean
```

## Example: NYC taxi with duplicates (FAIL)

```bash
gavel sandbox taxi-duplicate-rows
```

## Authoring a sandbox

Create `sandboxes/<name>/sandbox.yaml`:

```yaml
name: taxi-clean
version: "1"
components:
  data_warehouse:
    type: postgres
datasets:
  golden:
    source: file
    path: golden/trips.json
  candidate:
    source: file
    path: candidate/trips.json
metrics:
  - name: row_count
    golden: golden.trip_count
    candidate: candidate.trip_count
    fn: exact
  - name: total_fare
    golden: golden.total_fare
    candidate: candidate.total_fare
    fn: exact
    tolerance: 0.01
```

Dataset files are JSON objects with `{"rows": [{}]}` structure.

## Supported metric functions

| fn | Purpose |
|----|---------|
| `exact` | Scalar equality (optional `tolerance` for floats) |
| `jaccard` | Polygon WKT overlap (`threshold`, default 0.95) |
| `area_ratio` | Relative area delta (`tolerance`, default 0.05) |
| `not_null` | Candidate column must be present |
| `row_count` | Compare dataset sizes via `golden.rows` / `candidate.rows` |
| `gte` / `lte` | Threshold checks on candidate values |

## Roadmap

- [x] Snapshot golden/candidate JSON datasets
- [ ] Live adapters for production data warehouses
- [ ] Signed evidence bundles
- [ ] Policy-gated pull-request integration
