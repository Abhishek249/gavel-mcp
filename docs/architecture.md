# Gavel architecture

Gavel separates **judgment** (deterministic eval) from **collection** (adapters that talk to your infra).

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Sandbox spec│     │ Golden / candidate│     │ Metric DSL      │
│ (YAML)      │     │ datasets          │     │ jaccard, exact… │
└──────┬──────┘     └────────┬─────────┘     └────────┬────────┘
       │                     │                        │
       └─────────────────────┼────────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │ Eval engine     │  ← no LLM, no network
                    │ ValidationReport│
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ MCP stdio server│  ← agents call tools here
                    └─────────────────┘
```

## Layers

| Layer | Package | Role |
|-------|---------|------|
| Spec | `gavel/sandbox/` | Load `sandboxes/*/sandbox.yaml`, align rows, run metrics |
| Adapters | `gavel/adapters/` | Postgres, WO HTTP, Dagster GraphQL (live only) |
| Collectors | `gavel/collectors/` | Compose adapter output into candidate evidence rows |
| Verdict | `gavel/geospatial.py`, `validators.py` | Legacy single-stage checks |
| MCP | `gavel/server.py` | Expose tools over stdio |

## Manual report DevInt flow

```
UI trigger → manual_report_id
       │
       ▼
collect_manual_report_candidate()
  ├─ Postgres: boundary_result, gap_count, aggregated_fov_wkt
  ├─ WO: autofov-{mr}, lisa-{mr}
  └─ Dagster: materialization metadata (tile_count, postgres_written, …)
       │
       ▼
validate_sandbox_run("manual-report-in1290", live=true)
  └─ compare candidate vs golden/proof2.json → ValidationReport
```

Poll Dagster with WO **`adapter_run_id`**, not WO `run_id`.

## MCP tools

| Tool | Network |
|------|---------|
| `validate_candidate_pipeline` | No |
| `validate_geospatial_run` | No |
| `list_sandbox_definitions` | No |
| `validate_sandbox_run` | No (unless you pass live params) |
| `collect_manual_report_candidate_row` | Yes (DevInt) |
| `validate_manual_report_live` | Yes (DevInt) |
