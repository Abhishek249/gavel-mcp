.PHONY: help install test lint prove benchmark demo smoke sandbox-offline sandbox-fail mcp-config docs

PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
SANDBOX ?= taxi-clean

help:
	@echo "Gavel local commands:"
	@echo "  make install          Create .venv and install [dev,live]"
	@echo "  make test             Run pytest (no network)"
	@echo "  make smoke            test + prove + sandbox-offline"
	@echo "  make prove            MCP boundary proof script"
	@echo "  make sandbox-offline  Validate taxi-clean (expect PASS)"
	@echo "  make sandbox-fail     Validate taxi-duplicate-rows (expect FAIL)"
	@echo "  make demo             Interactive MCP demo"
	@echo "  make mcp-config       Print Cursor MCP JSON snippet"

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -U pip
	$(BIN)/pip install -e ".[dev]"
	@echo "Installed. Run 'make smoke' to verify."

test:
	$(BIN)/pytest --cov=gavel --cov-report=term-missing

lint:
	$(BIN)/ruff check .

prove:
	$(BIN)/python scripts/prove_it.py

benchmark:
	$(BIN)/python scripts/benchmark_mcp.py --output benchmark-report.json

demo:
	$(BIN)/python scripts/demo_live.py

sandbox-offline:
	$(BIN)/gavel sandbox $(SANDBOX) \
		--params '{"candidate_key":"trip-0000000"}'

sandbox-fail:
	$(BIN)/gavel sandbox taxi-duplicate-rows \
		--params '{"candidate_key":"trip-0000000"}' \
		|| test $$? -eq 1

smoke: lint test prove sandbox-offline sandbox-fail
	@echo "smoke: PASS (offline)"

mcp-config:
	@ROOT="$$(cd "$(CURDIR)" && pwd)"; \
	echo "Add to Cursor MCP settings (merge into mcpServers):"; \
	echo "{"; \
	echo '  "gavel": {'; \
	echo "    \"command\": \"$$ROOT/$(BIN)/gavel-mcp\","; \
	echo '    "args": [],'; \
	echo '    "env": {'; \
	echo "      \"GAVEL_SANDBOX_DIR\": \"$$ROOT/sandboxes\""; \
	echo '    }'; \
	echo '  }'; \
	echo "}"
