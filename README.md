<p align="center">
  <img src="assets/proofline-logo-tagline.png" alt="Proofline — evidence-based validation for agentic data pipelines" width="220">
</p>

<h1 align="center">Proofline MCP</h1>

<h3 align="center">Prove your pipeline data landed — not just that the job turned green.</h3>

<p align="center">
  Declarative sandbox evals for agent-built data pipelines. Golden vs candidate datasets,
  deterministic metrics (Jaccard, exact, area ratio), and a local MCP server your coding agent can call.
  <strong>The LLM decides when to validate; Proofline decides pass or fail.</strong>
</p>

<p align="center">
  <a href="https://github.com/Abhishek249/proofline-mcp/actions/workflows/ci.yml"><img src="https://github.com/Abhishek249/proofline-mcp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-16a085" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/MCP-stdio-6f42c1" alt="MCP stdio">
  <img src="https://img.shields.io/badge/python-3.11+-3776ab" alt="Python 3.11+">
</p>

## 🚀 Quick start

Prerequisites: **Python 3.11+**. Live DevInt validation also needs network access to `10.51.50.91`.

```bash
git clone https://github.com/Abhishek249/proofline-mcp.git
cd proofline-mcp
make install          # creates .venv, copies .env.example → .env
make smoke            # lint + 21 tests + MCP prove + offline sandboxes — no secrets
```

**Keys, honestly:**

| What | Credentials |
|------|-------------|
| `make smoke`, `pytest`, offline sandboxes | **None** — runs fully local |
| Live manual-report collect/validate | **`PGPASSWORD`** (+ optional WO/Dagster URLs; defaults to DevInt `.91`) |
| MCP in Cursor | Point at `.venv/bin/proofline-mcp` — see [`docs/mcp-setup.md`](docs/mcp-setup.md) |
| SQL Server dual-write (PH-2683) | **Not wired yet** — use offline `q2755-dual-write` sandbox |

```bash
# Offline — IN-1290 Proof #2 golden vs packaged candidate (expect PASS)
make sandbox-offline

# Live — after setting PGPASSWORD in .env
make validate-mr
```

## 📚 Releases (what shipped when)

| Version | Focus | Try it |
|---------|-------|--------|
| **v0.1** | Taxi benchmark + geospatial evidence MCP tools | `proofline taxi` |
| **v0.2** | Sandbox spec + golden/candidate + metric DSL | `make sandbox-offline` |
| **v0.3** | Live DevInt collector (Postgres + WO + Dagster) | `make validate-mr` |

Full sandbox spec: [`docs/sandbox-platform.md`](docs/sandbox-platform.md) · Architecture: [`docs/architecture.md`](docs/architecture.md)

## 🧰 MCP server (local)

```bash
make mcp-config    # prints JSON snippet for Cursor
```

Six tools:

| MCP tool | Purpose |
|----------|---------|
| `list_sandbox_definitions` | Discover sandboxes under `sandboxes/` |
| `validate_sandbox_run` | Golden vs candidate metrics (snapshot or inline rows) |
| `collect_manual_report_candidate_row` | Live DevInt evidence for one `manual_report_id` |
| `validate_manual_report_live` | Collect + validate in one call |
| `validate_candidate_pipeline` | Synthetic NYC taxi reference vs candidate |
| `validate_geospatial_run` | BYO orchestrator/worker/DB evidence envelope |

Restart Cursor after editing MCP config. Walkthrough: [`docs/mcp-setup.md`](docs/mcp-setup.md).

## ✨ What's inside

- **Declarative sandboxes** — YAML spec: components, golden/candidate datasets, metric rubric
- **Deterministic metrics** — `exact`, `jaccard`, `area_ratio`, `not_null`, `row_count`, `gte`, `lte`
- **Silent-success detection** — green Dagster run but no `boundary_result` row, no polygon, no Postgres write
- **Shipped examples** — `manual-report-in1290` (Proof #2 PASS), `q2755-dual-write` (shape drift FAIL)
- **Live DevInt adapters** — Postgres + WO + Dagster GraphQL for manual-report runs
- **Structured evidence reports** — every check: name, expected, actual, status, context
- **MCP stdio boundary** — real client/server tests in CI (`prove_it.py`, benchmark)

Stack: Python, Pydantic, Shapely, PyYAML, MCP SDK, optional psycopg.

## 🏗️ Architecture

```
sandbox.yaml  →  golden.json + candidate (file | live collect)
                      ↓
                 metric engine (deterministic)
                      ↓
                 ValidationReport  →  MCP tool response
```

Manual report on DevInt (IN-1290):

```
manual_report_id
    → collect: Postgres + WO (autofov-{mr}, lisa-{mr}) + Dagster (adapter_run_id)
    → validate: compare vs sandboxes/manual-report-in1290/golden/proof2.json
```

**Rule:** poll Dagster with WO **`adapter_run_id`**, not WO `run_id`.

## 📂 Project structure

```
proofline-mcp/
├── sandboxes/
│   ├── manual-report-in1290/   # Proof #2 golden + metrics
│   └── q2755-dual-write/       # PH-2683-style shape drift
├── src/proofline/
│   ├── server.py               # MCP stdio server (6 tools)
│   ├── cli.py                  # proofline CLI
│   ├── sandbox/                # spec loader, metrics, runner
│   ├── adapters/               # Postgres, WO, Dagster HTTP clients
│   └── collectors/             # manual_report evidence composer
├── scripts/
│   ├── prove_it.py             # MCP boundary proof
│   ├── demo_live.py            # interactive demo
│   └── validate_manual_report_devint.sh
├── docs/
│   ├── mcp-setup.md
│   ├── architecture.md
│   └── sandbox-platform.md
├── Makefile
├── .env.example
└── tests/                      # 21 tests, network mocked
```

## 🔧 Commands

```bash
make install           # venv + pip install -e ".[dev,live]"
make test              # pytest
make smoke             # lint + test + prove + offline sandboxes
make prove             # MCP boundary script
make sandbox-offline   # IN-1290 Proof #2 offline validation
make sandbox-q2755     # dual-write drift (expect fail)
make validate-mr       # live DevInt (needs .env + PGPASSWORD)
make collect-mr        # live collect only
make demo              # interactive MCP demo
make mcp-config        # Cursor MCP JSON snippet
make lint              # ruff
```

CLI equivalents:

```bash
proofline list-sandboxes
proofline smoke
proofline sandbox manual-report-in1290 --params '{"candidate_key":"f6b07a32-..."}'
proofline validate-manual-report f6b07a32-ff8b-45b2-a784-cd38ff2d7213
```

## 🛠️ Troubleshooting

- **`PGPASSWORD is required`**: copy `.env.example` → `.env`, set DevInt Postgres password.
- **`manual_report not found`**: wrong UUID or MR deleted from DevInt.
- **Live PASS but you expected FAIL**: golden snapshot may be stale — capture a new golden or compare different MR.
- **MCP tools missing in Cursor**: run `make mcp-config`, use absolute paths, restart Cursor.
- **WO SUCCEEDED but geospatial check failed**: Proofline now accepts `SUCCEEDED`; re-run `make smoke`.
- **Dagster poll fails**: use `adapter_run_id` from WO job, not WO `run_id`.

## 📊 Taxi benchmark (v0.1)

Controlled fault injection on synthetic NYC taxi data — [verified benchmark record](docs/verified-benchmark-2026-09-10.md):

| Signal | Result |
|--------|-------:|
| Defect detection recall | 100% |
| False-positive rate | 0% |
| MCP call latency p50 | ~3 ms |

These numbers apply to the **published taxi fault model**, not arbitrary production pipelines.

## Roadmap

- [x] Sandbox eval platform + live DevInt manual-report collector
- [ ] SQL Server adapter for PH-2683 Q2755 dual-write
- [ ] Signed evidence bundles · OTel traces · PR gates

---

<p align="center"><strong>Clone it, <code>make smoke</code>, add MCP config, then <code>make validate-mr</code> when you have DevInt creds.</strong></p>

## 📄 License

MIT — see [LICENSE](LICENSE).
