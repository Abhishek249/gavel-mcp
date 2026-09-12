.PHONY: help install test lint prove benchmark demo smoke sandbox-offline sandbox-q2755 validate-mr collect-mr mcp-config docs

PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
MR_ID ?= f6b07a32-ff8b-45b2-a784-cd38ff2d7213
SANDBOX ?= manual-report-in1290

help:
	@echo "Proofline local commands:"
	@echo "  make install          Create .venv and install [dev,live]"
	@echo "  make test             Run pytest (no network)"
	@echo "  make smoke            test + prove + sandbox-offline"
	@echo "  make prove            MCP boundary proof script"
	@echo "  make sandbox-offline  Validate IN-1290 golden vs packaged candidate"
	@echo "  make sandbox-q2755    Validate Q2755 dual-write (expect FAIL)"
	@echo "  make validate-mr      Live DevInt collect + validate (needs .env)"
	@echo "  make collect-mr       Live DevInt collect only (needs .env)"
	@echo "  make demo             Interactive MCP demo"
	@echo "  make mcp-config       Print Cursor MCP JSON snippet"
	@echo "  MR_ID=<uuid> make validate-mr   Override manual report id"

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -U pip
	$(BIN)/pip install -e ".[dev,live]"
	@test -f .env || cp .env.example .env
	@echo "Installed. Copy .env.example -> .env and set PGPASSWORD for live DevInt."

test:
	$(BIN)/pytest --cov=proofline --cov-report=term-missing

lint:
	$(BIN)/ruff check .

prove:
	$(BIN)/python scripts/prove_it.py

benchmark:
	$(BIN)/python scripts/benchmark_mcp.py --output benchmark-report.json

demo:
	$(BIN)/python scripts/demo_live.py

sandbox-offline:
	$(BIN)/proofline sandbox $(SANDBOX) \
		--params '{"candidate_key":"$(MR_ID)"}'

sandbox-q2755:
	$(BIN)/proofline sandbox q2755-dual-write \
		--params '{"candidate_key":"3df9572e-73bf-45e6-86eb-fcc2e30d7ee0"}' \
		|| test $$? -eq 1

smoke: lint test prove sandbox-offline sandbox-q2755
	@echo "smoke: PASS (offline)"

validate-mr:
	@test -f .env || (echo "Missing .env — run: cp .env.example .env"; exit 1)
	@set -a && . ./.env && set +a && \
		test -n "$$PGPASSWORD" || (echo "Set PGPASSWORD in .env"; exit 1) && \
		$(BIN)/proofline validate-manual-report $${PROOFLINE_MR_ID:-$(MR_ID)} --sandbox $(SANDBOX)

collect-mr:
	@test -f .env || (echo "Missing .env — run: cp .env.example .env"; exit 1)
	@set -a && . ./.env && set +a && \
		test -n "$$PGPASSWORD" || (echo "Set PGPASSWORD in .env"; exit 1) && \
		$(BIN)/proofline collect-manual-report $${PROOFLINE_MR_ID:-$(MR_ID)}

mcp-config:
	@ROOT="$$(cd "$(CURDIR)" && pwd)"; \
	echo "Add to Cursor MCP settings (merge into mcpServers):"; \
	echo "{"; \
	echo '  "proofline": {'; \
	echo "    \"command\": \"$$ROOT/$(BIN)/proofline-mcp\","; \
	echo '    "args": [],'; \
	echo '    "env": {'; \
	echo "      \"PROOFLINE_SANDBOX_DIR\": \"$$ROOT/sandboxes\""; \
	echo '    }'; \
	echo '  }'; \
	echo "}"
