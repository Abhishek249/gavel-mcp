# Cursor MCP setup (local Gavel server)

## 1. Install and smoke-test offline

```bash
cd gavel-mcp
make install
make smoke
```

No credentials required for `make smoke`.

## 2. Add Gavel to Cursor

From the repo root:

```bash
make mcp-config
```

Copy the printed JSON into your Cursor MCP config (`~/.cursor/mcp.json` or project settings). Example:

```json
{
  "mcpServers": {
    "gavel": {
      "command": "/absolute/path/gavel-mcp/.venv/bin/gavel-mcp",
      "env": {
        "GAVEL_SANDBOX_DIR": "/absolute/path/gavel-mcp/sandboxes"
      }
    }
  }
}
```

Restart Cursor. You should see four tools:

- `validate_candidate_pipeline`
- `validate_geospatial_run`
- `list_sandbox_definitions`
- `validate_sandbox_run`

## 3. Try in chat

Offline:

> Call `validate_sandbox_run` with sandbox `taxi-clean`

Expected: `status: "pass"` with 3 passing checks (row_count, total_fare, unique_trip_count).
