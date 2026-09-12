from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from gavel.collectors.manual_report import collect_manual_report_candidate
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


def _cmd_collect_manual_report(args: argparse.Namespace) -> None:
    row = collect_manual_report_candidate(args.manual_report_id)
    payload = {"rows": [row]}
    text = json.dumps(payload, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(text, end="")


def _cmd_validate_manual_report(args: argparse.Namespace) -> None:
    params = {
        "live": True,
        "candidate_key": args.manual_report_id,
        "manual_report_id": args.manual_report_id,
    }
    if args.params:
        params.update(json.loads(args.params))
    report = run_sandbox_validation(args.sandbox, params=params)
    if args.output:
        Path(args.output).write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(report.model_dump_json(indent=2))
    if report.status.value == "fail":
        sys.exit(1)


def _cmd_list_sandboxes(_: argparse.Namespace) -> None:
    print(json.dumps(list_sandboxes(), indent=2))


def _cmd_smoke(_: argparse.Namespace) -> None:
    from gavel.models import CheckStatus

    report = run_sandbox_validation(
        "manual-report-in1290",
        params={"candidate_key": "f6b07a32-ff8b-45b2-a784-cd38ff2d7213"},
    )
    if report.status != CheckStatus.PASS:
        print("smoke failed: manual-report-in1290 offline validation", file=sys.stderr)
        sys.exit(1)
    q2755 = run_sandbox_validation(
        "q2755-dual-write",
        params={"candidate_key": "3df9572e-73bf-45e6-86eb-fcc2e30d7ee0"},
    )
    if q2755.status != CheckStatus.FAIL:
        print("smoke failed: q2755-dual-write should fail jaccard", file=sys.stderr)
        sys.exit(1)
    print('{"smoke":"pass","offline_sandboxes":["manual-report-in1290","q2755-dual-write"]}')


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
    sandbox.add_argument(
        "--live",
        action="store_true",
        help="Collect candidate rows live from DevInt adapters (requires env creds)",
    )
    sandbox.set_defaults(func=_cmd_sandbox)

    collect = subparsers.add_parser(
        "collect-manual-report",
        help="Collect manual-report candidate evidence from DevInt",
    )
    collect.add_argument("manual_report_id", help="manual_report UUID")
    collect.add_argument("-o", "--output", help="Write JSON dataset file")
    collect.set_defaults(func=_cmd_collect_manual_report)

    validate = subparsers.add_parser(
        "validate-manual-report",
        help="Live-collect + validate a manual report against a sandbox golden dataset",
    )
    validate.add_argument("manual_report_id", help="manual_report UUID")
    validate.add_argument(
        "--sandbox",
        default="manual-report-in1290",
        help="Sandbox definition name (default: manual-report-in1290)",
    )
    validate.add_argument("--params", help="Extra JSON params merged into validation")
    validate.add_argument("-o", "--output", help="Write validation report JSON")
    validate.set_defaults(func=_cmd_validate_manual_report)

    listing = subparsers.add_parser("list-sandboxes", help="List available sandbox definitions")
    listing.set_defaults(func=_cmd_list_sandboxes)

    smoke = subparsers.add_parser("smoke", help="Offline sandbox smoke check")
    smoke.set_defaults(func=_cmd_smoke)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
