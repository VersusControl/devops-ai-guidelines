"""Validate a captured case and add it to the pinned cohort."""

import argparse
import json
from datetime import date
from pathlib import Path

from case_lifecycle import register_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="Captured scenario, usually under inbox/")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).parent / "manifest.json")
    parser.add_argument("--covers", required=True, help="Coverage label, such as cache_stampede")
    parser.add_argument("--today", help="ISO review date, for a drill")
    parser.add_argument("--apply", action="store_true", help="Write the manifest and copy the case")
    args = parser.parse_args()
    today = date.fromisoformat(args.today) if args.today else date.today()
    result = register_case(args.manifest, args.draft, args.covers, apply=args.apply, today=today)
    print(json.dumps(result, indent=2))
    if result["dry_run"]:
        print("Dry run: add --apply to register the case.")


if __name__ == "__main__":
    main()
