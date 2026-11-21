"""Retire a case while keeping its reason and replacement in the manifest."""

import argparse
import json
from datetime import date
from pathlib import Path

from case_lifecycle import retire_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Active case to retire")
    parser.add_argument("--reason", required=True, help="Why the case no longer represents the system")
    parser.add_argument("--owner", required=True, help="Person or team who reviewed the retirement")
    parser.add_argument("--replaced-by", default="", help="Active case that takes its place")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).parent / "manifest.json")
    parser.add_argument("--today", help="ISO review date, for a drill")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    today = date.fromisoformat(args.today) if args.today else date.today()
    result = retire_case(
        args.manifest,
        args.id,
        args.reason,
        args.owner,
        replaced_by=args.replaced_by,
        apply=args.apply,
        today=today,
    )
    print(json.dumps(result, indent=2))
    if result["dry_run"]:
        print("Dry run: add --apply to retire the case.")


if __name__ == "__main__":
    main()
