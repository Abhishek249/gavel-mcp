# Gavel architecture

Gavel separates **judgment** (deterministic eval) from **collection** (evidence gathering).

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
| Verdict | `gavel/geospatial.py`, `validators.py` | Specialized checks |
| MCP | `gavel/server.py` | Expose tools over stdio |

## NYC taxi sandbox flow

```
Agent decides to validate
       │
       ▼
validate_sandbox_run("taxi-clean")
  ├─ Load golden: sandboxes/taxi-clean/golden/trips.json
  ├─ Load candidate: sandboxes/taxi-clean/candidate/trips.json
  └─ Run metrics: row_count, total_fare, unique_trip_count
       │
       ▼
ValidationReport → PASS/FAIL
```

## MCP tools

| Tool | Network |
|------|---------|
| `validate_candidate_pipeline` | No |
| `validate_geospatial_run` | No |
| `list_sandbox_definitions` | No |
| `validate_sandbox_run` | No |
