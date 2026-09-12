from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PostgresSettings:
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> PostgresSettings:
        password = (
            os.environ.get("PGPASSWORD")
            or os.environ.get("GAVEL_PG_PASSWORD")
            or os.environ.get("PROOFLINE_PG_PASSWORD")
        )
        if not password:
            raise RuntimeError(
                "PGPASSWORD, GAVEL_PG_PASSWORD, or PROOFLINE_PG_PASSWORD is required for live Postgres access"
            )
        return cls(
            host=os.environ.get("PGHOST", "10.51.50.91"),
            port=int(os.environ.get("PGPORT", "5432")),
            database=os.environ.get("PGDATABASE", "pcubed_pro"),
            user=os.environ.get("PGUSER", "admin"),
            password=password,
        )


def fetch_rows(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a read-only SQL query and return rows as dicts."""
    settings = PostgresSettings.from_env()
    try:
        return _fetch_rows_psycopg(sql, params or {}, settings)
    except ImportError:
        return _fetch_rows_psql(sql, params or {}, settings)


def _fetch_rows_psycopg(
    sql: str, params: dict[str, Any], settings: PostgresSettings
) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.database,
        user=settings.user,
        password=settings.password,
        row_factory=dict_row,
    ) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def _fetch_rows_psql(
    sql: str, params: dict[str, Any], settings: PostgresSettings
) -> list[dict[str, Any]]:
    if not shutil.which("psql"):
        raise RuntimeError("install psycopg (`pip install gavel-mcp[live]`) or psql for Postgres access")

    rendered = sql
    for key, value in params.items():
        rendered = rendered.replace(f"%({key})s", _psql_literal(value))

    env = os.environ.copy()
    env.update(
        {
            "PGHOST": settings.host,
            "PGPORT": str(settings.port),
            "PGDATABASE": settings.database,
            "PGUSER": settings.user,
            "PGPASSWORD": settings.password,
        }
    )
    cmd = [
        "psql",
        "-h",
        settings.host,
        "-p",
        str(settings.port),
        "-U",
        settings.user,
        "-d",
        settings.database,
        "-c",
        f"SELECT json_agg(t) FROM ({rendered}) t;",
    ]
    output = subprocess.check_output(cmd, env=env, text=True, stderr=subprocess.STDOUT).strip()
    if not output or output in {"[null]", "null"}:
        return []
    payload = json.loads(output)
    if payload is None:
        return []
    if isinstance(payload, list):
        return [dict(row) for row in payload]
    return [dict(payload)]


def _psql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"
