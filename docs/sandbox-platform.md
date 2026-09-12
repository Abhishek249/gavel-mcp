# Sandbox eval platform

Gavel v0.2 adds a declarative **sandbox eval** layer:

1. **Spec** — declare sandbox components (Postgres, SQL Server, Dagster, WO, S3, …)
2. **Golden + candidate datasets** — JSON snapshots (v1) or future live adapters
3. **Metrics** — deterministic rubric comparing `golden.col` vs `candidate.col`

Agents invoke validation through MCP:

- `list_sandbox_definitions()`
- `validate_sandbox_run(sandbox, params?, candidate_rows?, candidate_path?)`

## Example: Manual Report IN-1290

```bash
gavel sandbox manual-report-in1290 \
  --params '{"candidate_key":"f6b07a32-ff8b-45b2-a784-cd38ff2d7213"}'
```

## Example: PH-2683 Q2755 dual-write (fails packaged drift candidate)

```bash
gavel sandbox q2755-dual-write \
  --params '{"candidate_key":"3df9572e-73bf-45e6-86eb-fcc2e30d7ee0"}'
```

## Authoring a sandbox

Create `sandboxes/<name>/sandbox.yaml`:

```yaml
name: my-sandbox
version: "1"
components:
  postgres_qa:
    type: postgres
datasets:
  golden:
    source: file
    path: golden/data.json
    key: id
  candidate:
    source: file
    path: candidate/data.json
    key: id
align:
  golden_key: id
  candidate_key: id
metrics:
  - name: shape_jaccard
    golden: golden.geom_wkt
    candidate: candidate.geom_wkt
    fn: jaccard
    threshold: 0.95
```

Dataset files are JSON arrays or `{"rows": [...]}` objects.

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
- [x] Live DevInt collector for manual-report (`collect-manual-report`, `validate-manual-report`)
- [ ] SQL Server adapter for PH-2683 Q2755 dual-write
- [ ] Signed evidence bundles
- [ ] Policy-gated pull-request integration

## Live DevInt manual report workflow

Requires DevInt credentials (see `docs/DEVINT-CHEATSHEET.md` in pcp-repos):

```bash
export PGHOST=10.51.50.91 PGPORT=5432 PGDATABASE=pcubed_pro PGUSER=admin
export PGPASSWORD='...'
export GAVEL_WO_URL=http://10.51.50.91:8001
export GAVEL_DAGSTER_URL=http://10.51.50.91:3001

pip install -e ".[live]"

# Collect candidate evidence only
gavel collect-manual-report f6b07a32-ff8b-45b2-a784-cd38ff2d7213 -o /tmp/candidate.json

# Collect + validate against golden snapshot (Proof #2)
gavel validate-manual-report f6b07a32-ff8b-45b2-a784-cd38ff2d7213

# Or use the helper script
./scripts/validate_manual_report_devint.sh f6b07a32-ff8b-45b2-a784-cd38ff2d7213
```

MCP tools for agents:

- `collect_manual_report_candidate_row(manual_report_id)`
- `validate_manual_report_live(manual_report_id, sandbox="manual-report-in1290")`
