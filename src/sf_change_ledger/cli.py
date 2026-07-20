from __future__ import annotations

import argparse
import sys

from sf_change_ledger.diff import compare_snapshots
from sf_change_ledger.ingest import load_snapshot
from sf_change_ledger.report import write_report
from sf_change_ledger.risk import assess_diff


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sf-change-ledger",
        description="Semantic version ledger for SAP SuccessFactors configuration exports",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    compare = subparsers.add_parser("compare", help="Compare two configuration snapshots")
    compare.add_argument("--left", required=True, help="Baseline snapshot folder")
    compare.add_argument("--right", required=True, help="New snapshot folder")
    compare.add_argument("--left-label", help="Friendly label for the baseline snapshot")
    compare.add_argument("--right-label", help="Friendly label for the new snapshot")
    compare.add_argument("--out", required=True, help="Report path (.md, .html, .xlsx, or .json)")
    return parser


def run_compare(args: argparse.Namespace) -> int:
    left = load_snapshot(args.left, args.left_label)
    right = load_snapshot(args.right, args.right_label)
    result = assess_diff(compare_snapshots(left, right))
    write_report(result, args.out)
    print(
        "Compared snapshots:",
        f"objects={len(left.objects)}->{len(right.objects)}",
        f"changes={len(result.changes)}",
        f"critical={result.by_severity.get('CRITICAL', 0)}",
        f"high={result.by_severity.get('HIGH', 0)}",
    )
    print(f"Wrote report: {args.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "compare":
            return run_compare(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
