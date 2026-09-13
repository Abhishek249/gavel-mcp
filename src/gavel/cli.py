from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from gavel.runner import run_validation
from gavel.sandbox.loader import list_sandboxes
from gavel.sandbox.runner import run_sandbox_validation


def _load_dotenv(path: Path | None = None) -> None:
    env_path = path or Path(".env")
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _cmd_taxi(args: argparse.Namespace) -> None:
    report = run_validation(faults=args.fault, row_count=args.rows, seed=args.seed)
    print(report.model_dump_json(indent=2))


def _cmd_sandbox(args: argparse.Namespace) -> None:
    params = json.loads(args.params) if args.params else {}
    if args.live:
        params["live"] = True
    report = run_sandbox_validation(
        args.name,
        params=params,
        candidate_path=args.candidate,
    )
    print(report.model_dump_json(indent=2))
    if report.status.value == "fail":
        sys.exit(1)


def _cmd_list_sandboxes(_: argparse.Namespace) -> None:
    print(json.dumps(list_sandboxes(), indent=2))


def _cmd_smoke(_: argparse.Namespace) -> None:
    from gavel.models import CheckStatus

    report = run_sandbox_validation(
        "taxi-clean",
        params={"candidate_key": "trip-0000000"},
    )
    if report.status != CheckStatus.PASS:
        print("smoke failed: taxi-clean offline validation", file=sys.stderr)
        sys.exit(1)
    dup = run_sandbox_validation(
        "taxi-duplicate-rows",
        params={"candidate_key": "trip-0000000"},
    )
    if dup.status != CheckStatus.FAIL:
        print("smoke failed: taxi-duplicate-rows should fail", file=sys.stderr)
        sys.exit(1)
    print('{"smoke":"pass","offline_sandboxes":["taxi-clean","taxi-duplicate-rows"]}')


def main() -> None:
    _load_dotenv()
    parser = argparse.ArgumentParser(description="Gavel validation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    taxi = subparsers.add_parser("taxi", help="Run synthetic taxi benchmark validation")
    taxi.add_argument("--fault", action="append", default=[], help="Inject a known defect")
    taxi.add_argument("--rows", type=int, default=1_000)
    taxi.add_argument("--seed", type=int, default=42)
    taxi.set_defaults(func=_cmd_taxi)

    sandbox = subparsers.add_parser("sandbox", help="Run a declarative sandbox eval")
    sandbox.add_argument("name", help="Sandbox folder name under sandboxes/")
    sandbox.add_argument(
        "--params",
        help='JSON object for alignment keys, e.g. \'{"candidate_key":"..."}\'',
    )
    sandbox.add_argument("--candidate", help="Optional candidate JSON file override")
    sandbox.set_defaults(func=_cmd_sandbox)

    listing = subparsers.add_parser("list-sandboxes", help="List available sandbox definitions")
    listing.set_defaults(func=_cmd_list_sandboxes)

    smoke = subparsers.add_parser("smoke", help="Offline sandbox smoke check")
    smoke.set_defaults(func=_cmd_smoke)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
