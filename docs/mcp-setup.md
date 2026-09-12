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

Restart Cursor. You should see six tools:

- `validate_candidate_pipeline`
- `validate_geospatial_run`
- `list_sandbox_definitions`
- `validate_sandbox_run`
- `collect_manual_report_candidate_row`
- `validate_manual_report_live`

## 3. Live DevInt tools (optional)

Add Postgres and orchestration env vars to the MCP server block:

```json
"env": {
  "GAVEL_SANDBOX_DIR": "/absolute/path/gavel-mcp/sandboxes",
  "PGHOST": "10.51.50.91",
  "PGPORT": "5432",
  "PGDATABASE": "pcubed_pro",
  "PGUSER": "admin",
  "PGPASSWORD": "your-devint-password",
  "GAVEL_WO_URL": "http://10.51.50.91:8001",
  "GAVEL_DAGSTER_URL": "http://10.51.50.91:3001"
}
```

Do not commit passwords. Use `.env` locally for CLI; MCP config is local-only.

## 4. Try in chat

Offline:

> Call `validate_sandbox_run` with sandbox `manual-report-in1290` and params `{"candidate_key": "f6b07a32-ff8b-45b2-a784-cd38ff2d7213"}`

Live (after env configured):

> Call `validate_manual_report_live` with manual_report_id `f6b07a32-ff8b-45b2-a784-cd38ff2d7213`

Expected: `status: "pass"` if DevInt still matches Proof #2 golden snapshot.
