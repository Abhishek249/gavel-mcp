from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from proofline.collectors.manual_report import collect_manual_report_candidate
from proofline.runner import run_validation
from proofline.sandbox.loader import list_sandboxes
from proofline.sandbox.runner import run_sandbox_validation


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Proofline validation CLI")
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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
