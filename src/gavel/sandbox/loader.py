from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from gavel.sandbox.spec import SandboxSpec


def default_sandbox_dir() -> Path:
    env = os.environ.get("GAVEL_SANDBOX_DIR") or os.environ.get("PROOFLINE_SANDBOX_DIR")
    if env:
        return Path(env).expanduser().resolve()

    installed = Path(__file__).resolve().parents[1] / "sandboxes"
    if installed.is_dir():
        return installed

    repo_candidate = Path(__file__).resolve().parents[3] / "sandboxes"
    if repo_candidate.is_dir():
        return repo_candidate

    cwd_candidate = Path.cwd() / "sandboxes"
    if cwd_candidate.is_dir():
        return cwd_candidate
    return repo_candidate


def list_sandboxes(root: Path | None = None) -> list[dict[str, str]]:
    sandbox_root = (root or default_sandbox_dir()).resolve()
    if not sandbox_root.is_dir():
        return []

    discovered: list[dict[str, str]] = []
    for child in sorted(sandbox_root.iterdir()):
        if not child.is_dir():
            continue
        spec_path = child / "sandbox.yaml"
        if not spec_path.is_file():
            continue
        spec = load_sandbox_spec(child.name, root=sandbox_root)
        discovered.append(
            {
                "name": spec.name,
                "version": spec.version,
                "description": spec.description or "",
                "path": str(child),
            }
        )
    return discovered


def load_sandbox_spec(name: str, root: Path | None = None) -> SandboxSpec:
    sandbox_root = (root or default_sandbox_dir()).resolve()
    sandbox_dir = sandbox_root / name
    spec_path = sandbox_dir / "sandbox.yaml"
    if not spec_path.is_file():
        raise FileNotFoundError(f"sandbox '{name}' not found at {spec_path}")

    raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec = SandboxSpec.model_validate(raw)
    if spec.name != name:
        raise ValueError(f"sandbox folder '{name}' does not match spec.name '{spec.name}'")
    return spec


def sandbox_dir_for(name: str, root: Path | None = None) -> Path:
    sandbox_root = (root or default_sandbox_dir()).resolve()
    return sandbox_root / name


def load_dataset_rows(
    dataset_name: str,
    dataset_spec,
    *,
    sandbox_dir: Path,
    inline_override: list[dict] | None = None,
    file_override: Path | None = None,
) -> list[dict]:
    if inline_override is not None:
        return [dict(row) for row in inline_override]

    if dataset_spec.source == "inline":
        if not dataset_spec.rows:
            raise ValueError(f"datasets.{dataset_name} inline source requires rows")
        return [dict(row) for row in dataset_spec.rows]

    path = file_override
    if path is None:
        if not dataset_spec.path:
            raise ValueError(f"datasets.{dataset_name} file source requires path")
        path = sandbox_dir / dataset_spec.path

    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"datasets.{dataset_name} file not found: {path}")

    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(text)
        if isinstance(payload, dict) and "rows" in payload:
            rows = payload["rows"]
        elif isinstance(payload, list):
            rows = payload
        else:
            raise ValueError(f"{path} must be a JSON list or {{'rows': [...]}} object")
        return [dict(row) for row in rows]

    raise ValueError(f"unsupported dataset file type: {suffix}")
