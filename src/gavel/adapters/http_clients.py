from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def default_wo_url() -> str:
    return (
        os.environ.get("GAVEL_WO_URL")
        or os.environ.get("PROOFLINE_WO_URL")
        or os.environ.get("DEVINT_WO_URL")
        or "http://10.51.50.91:8001"
    )


def default_dagster_url() -> str:
    return (
        os.environ.get("GAVEL_DAGSTER_URL")
        or os.environ.get("PROOFLINE_DAGSTER_URL")
        or os.environ.get("DEVINT_DAGSTER_URL")
        or "http://10.51.50.91:3001"
    )


def http_json(method: str, url: str, body: dict[str, Any] | None = None, *, timeout: float = 60) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {detail}") from exc


def dagster_graphql(query: str, variables: dict[str, Any] | None = None, *, url: str | None = None) -> dict[str, Any]:
    payload = http_json(
        "POST",
        f"{url or default_dagster_url()}/graphql",
        {"query": query, "variables": variables or {}},
    )
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def list_wo_jobs(*, limit: int = 50, url: str | None = None) -> list[dict[str, Any]]:
    response = http_json("GET", f"{url or default_wo_url()}/v1/jobs?limit={limit}")
    jobs = response.get("result", response)
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs", jobs.get("items", []))
    if not isinstance(jobs, list):
        return []
    return jobs


def find_wo_job_by_name(name: str, *, url: str | None = None) -> dict[str, Any] | None:
    for job in list_wo_jobs(url=url):
        if job.get("name") == name:
            return job
    return None


def get_wo_job(job_id: str, *, url: str | None = None) -> dict[str, Any]:
    response = http_json("GET", f"{url or default_wo_url()}/v1/jobs/{job_id}")
    return response.get("result", response)


def dagster_run_status(run_id: str, *, url: str | None = None) -> str:
    query = """
    query($id: ID!) {
      pipelineRunOrError(runId: $id) {
        ... on Run { status }
      }
    }
    """
    data = dagster_graphql(query, {"id": run_id}, url=url)
    run = data["pipelineRunOrError"]
    if not run or "status" not in run:
        raise RuntimeError(f"Dagster run not found: {run_id}")
    return run["status"]


def dagster_materialization_metadata(run_id: str, *, url: str | None = None) -> dict[str, Any]:
    query = """
    query($runId: ID!) {
      logsForRun(runId: $runId) {
        ... on EventConnection {
          events {
            __typename
            ... on MaterializationEvent {
              metadataEntries {
                label
                ... on TextMetadataEntry { text }
                ... on FloatMetadataEntry { floatValue }
                ... on BoolMetadataEntry { boolValue }
                ... on IntMetadataEntry { intValue }
              }
            }
          }
        }
      }
    }
    """
    data = dagster_graphql(query, {"runId": run_id}, url=url)
    metadata: dict[str, Any] = {}
    events = data.get("logsForRun", {}).get("events", [])
    for event in events:
        if event.get("__typename") != "MaterializationEvent":
            continue
        for entry in event.get("metadataEntries", []):
            label = entry.get("label")
            if not label:
                continue
            value = (
                entry.get("text")
                if entry.get("text") is not None
                else entry.get("floatValue")
                if entry.get("floatValue") is not None
                else entry.get("boolValue")
                if entry.get("boolValue") is not None
                else entry.get("intValue")
            )
            metadata[label] = value
    return metadata


def find_dagster_run_by_manual_report(
    manual_report_id: str,
    pipeline_name: str,
    *,
    url: str | None = None,
    limit: int = 20,
) -> dict[str, Any] | None:
    query = """
    query($tag: String!, $limit: Int!) {
      runsOrError(
        filter: { tags: [{ key: "manual_report_id", value: $tag }] },
        limit: $limit
      ) {
        ... on Runs {
          results { runId status startTime pipelineName tags { key value } }
        }
      }
    }
    """
    data = dagster_graphql(query, {"tag": manual_report_id, "limit": limit}, url=url)
    runs = data.get("runsOrError", {}).get("results", [])
    matches = [run for run in runs if run.get("pipelineName") == pipeline_name]
    if not matches:
        return None
    return max(matches, key=lambda run: run.get("startTime") or 0)
