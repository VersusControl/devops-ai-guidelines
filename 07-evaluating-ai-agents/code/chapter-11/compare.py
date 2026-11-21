"""Compare two benchmark reports only when they scored the same pinned cohort."""

import argparse
import json
from pathlib import Path

from benchmark import compare_reports, format_comparison


def load_report(path):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"cohort_id", "cohort_fingerprint", "per_case", "overall", "attempts_per_case"}
    if not required <= report.keys():
        raise ValueError(f"{path} is not a benchmark report")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    comparison = compare_reports(load_report(args.baseline), load_report(args.candidate))
    print(format_comparison(comparison))
    print("\nAn overlapping interval is not evidence of improvement. Add attempts,")
    print("not adjectives, before you claim the change worked.")


if __name__ == "__main__":
    main()
