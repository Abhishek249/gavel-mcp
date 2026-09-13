<p align="center">
  <img src="assets/gavel-readme-banner.png" alt="Gavel — collect evidence, compare to golden, emit verdict" width="480">
</p>

<p align="center">
  Declarative sandbox evals for agent-built data pipelines. Golden vs candidate datasets,
  deterministic metrics (Jaccard, exact, area ratio), and a local MCP server your coding agent can call.
  <strong>The LLM decides when to validate; Gavel decides pass or fail.</strong>
</p>

<p align="center">
  <a href="https://github.com/Abhishek249/gavel-mcp/actions/workflows/ci.yml"><img src="https://github.com/Abhishek249/gavel-mcp/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-16a085" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/MCP-stdio-6f42c1" alt="MCP stdio">
  <img src="https://img.shields.io/badge/python-3.11+-3776ab" alt="Python 3.11+">
</p>

## 🚀 Quick start

Prerequisites: **Python 3.11+**.

```bash
git clone https://github.com/Abhishek249/gavel-mcp.git
cd gavel-mcp
make install          # creates .venv, copies .env.example → .env
make smoke            # lint + 22 tests + MCP prove + offline sandboxes — no secrets
```

**Try it:**

```bash
# Clean NYC taxi data (expect PASS)
gavel sandbox taxi-clean --params '{"candidate_key":"trip-0000000"}'

# Taxi data with duplicate rows (expect FAIL)
gavel sandbox taxi-duplicate-rows --params '{"candidate_key":"trip-0000000"}'
```

## 📚 Releases (what shipped when)

| Version | Focus | Try it |
|---------|-------|--------|
| **v0.4** | Renamed from Proofline → **Gavel** (`gavel` CLI, `gavel-mcp` server) | `make smoke` |
| **v0.1** | Taxi benchmark + geospatial evidence MCP tools | `gavel taxi` |
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
- **Silent-success detection** — catches green orchestration with missing/wrong data
- **Shipped examples** — NYC taxi clean data (PASS), duplicate rows (FAIL)
- **Structured evidence reports** — every check: name, expected, actual, status, context
- **MCP stdio boundary** — real client/server tests in CI (`prove_it.py`, benchmark)

Stack: Python, Pydantic, Shapely, PyYAML, MCP SDK.

## 🏗️ Architecture

```
sandbox.yaml  →  golden.json + candidate.json (file | inline | live)
                      ↓
                 metric engine (deterministic)
                      ↓
                 ValidationReport  →  MCP tool response
```

Example: NYC taxi duplicate-row detection

```
trip_id
    → load golden: 500 clean trips
    → load candidate: 600 trips (100 duplicates)
    → validate: row_count, key_uniqueness, fare_total → FAIL
```

## 📂 Project structure

```
gavel-mcp/
├── assets/
│   ├── gavel-readme-banner.png # README banner
│   └── gavel-icon.png          # square icon (social preview)
├── sandboxes/
│   ├── taxi-clean/             # Clean NYC taxi data (PASS)
│   └── taxi-duplicate-rows/    # Duplicate detection (FAIL)
├── src/gavel/
│   ├── server.py               # MCP stdio server (6 tools)
│   ├── cli.py                  # gavel CLI
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
make sandbox-offline   # taxi-clean validation (expect PASS)
make sandbox-fail      # taxi-duplicate-rows (expect FAIL)
make demo              # interactive MCP demo
make mcp-config        # Cursor MCP JSON snippet
make lint              # ruff
```

CLI equivalents:

```bash
gavel list-sandboxes
gavel smoke
gavel sandbox taxi-clean --params '{"candidate_key":"trip-0000000"}'
gavel sandbox taxi-duplicate-rows --params '{"candidate_key":"trip-0000000"}'
```

## 🛠️ Troubleshooting

- **MCP tools missing in Cursor**: run `make mcp-config`, use absolute paths, restart Cursor.
- **Sandbox not found**: check `sandboxes/` directory structure and YAML syntax.

## 📊 Taxi benchmark (v0.1)

Controlled fault injection on synthetic NYC taxi data — [verified benchmark record](docs/verified-benchmark-2026-09-10.md):

| Signal | Result |
|--------|-------:|
| Defect detection recall | 100% |
| False-positive rate | 0% |
| MCP call latency p50 | ~3 ms |

These numbers apply to the **published taxi fault model**, not arbitrary production pipelines.

## Roadmap

- [x] Sandbox eval platform with NYC taxi examples
- [ ] Live adapters for production data warehouses
- [ ] Signed evidence bundles · OTel traces · PR gates

---

<p align="center"><strong>Clone it, <code>make smoke</code>, add MCP config, then <code>make validate-mr</code> when you have DevInt creds.</strong></p>

## 📄 License

MIT — see [LICENSE](LICENSE).
