"""Gate a merge on agent quality and on the health of the suite that measured it."""

import argparse
import json
import textwrap
from datetime import date
from pathlib import Path

from benchmark import classify, load_manifest


def check_gate(report, manifest, today=None):
    today = today or date.today()
    cohort = classify(manifest, today)
    active_ids = [case.id for case in cohort.active]
    active_covers = {case.covers for case in cohort.active}
    policy = manifest.policy
    entries = {
        entry.get("case"): entry
        for entry in report.get("per_case", [])
        if isinstance(entry, dict)
    }
    checks = []

    def add(section, label, ok, detail=""):
        checks.append({"section": section, "label": label, "ok": bool(ok), "detail": detail})

    add("quality", "cohort fingerprint matches",
        report.get("cohort_fingerprint") == cohort.fingerprint,
        "" if report.get("cohort_fingerprint") == cohort.fingerprint
        else "rerun on the current manifest")
    missing = [case_id for case_id in active_ids if case_id not in entries]
    add("quality", "every active case scored", not missing,
        f"missing: {', '.join(missing)}" if missing else "")
    extra = sorted(set(entries) - set(active_ids))
    add("quality", "no inactive case scored", not extra,
        f"unexpected: {', '.join(extra)}" if extra else "")

    attempts = [entries[case_id].get("attempts", 0) for case_id in active_ids
                if case_id in entries]
    balanced = bool(attempts) and len(set(attempts)) == 1
    enough = balanced and all(value >= policy["min_attempts_per_case"] for value in attempts)
    if not attempts:
        attempt_detail = f"none scored (min {policy['min_attempts_per_case']})"
    elif balanced:
        attempt_detail = f"{attempts[0]} (min {policy['min_attempts_per_case']})"
    else:
        attempt_detail = f"counts: {attempts} (min {policy['min_attempts_per_case']})"
    add("quality", "attempts per case", enough, attempt_detail)

    ungraded = sum(entries[case_id].get("ungraded", 0) for case_id in active_ids
                   if case_id in entries)
    add("quality", "ungraded attempts", ungraded <= policy["max_ungraded_attempts"],
        f"{ungraded} (max {policy['max_ungraded_attempts']})")

    overall_rate = report.get("overall", {}).get("pass_rate", 0.0)
    add("quality", "overall pass rate", overall_rate >= policy["min_pass_rate"],
        f"{overall_rate:.0%} (min {policy['min_pass_rate']:.0%})")

    weak = [
        f"{case_id} {entries[case_id].get('pass_rate', 0.0):.0%}"
        for case_id in active_ids
        if case_id in entries
        and entries[case_id].get("pass_rate", 0.0) < policy["min_case_pass_rate"]
    ]
    add("quality", "per-case floor", not weak,
        f"below {policy['min_case_pass_rate']:.0%}: {', '.join(weak)}" if weak else "")

    expired = [entry.id for entry in cohort.expired]
    add("suite health", "no expired active cases", not expired,
        f"expired: {', '.join(expired)}" if expired else "")

    missing_coverage = [
        label for label in manifest.required_coverage if label not in active_covers
    ]
    add("suite health", "coverage complete", not missing_coverage,
        f"missing: {', '.join(missing_coverage)}" if missing_coverage else "")

    stale = []
    for case in cohort.historical:
        reviewed_at = date.fromisoformat(case.retired["reviewed_at"])
        if (today - reviewed_at).days > policy["max_retirement_age_days"]:
            stale.append(case.id)
    add("suite health", "exclusions reviewed", not stale,
        f"stale: {', '.join(stale)}" if stale else "")

    quality_ok = all(check["ok"] for check in checks if check["section"] == "quality")
    health_ok = all(check["ok"] for check in checks if check["section"] == "suite health")
    return {
        "ok": quality_ok and health_ok,
        "quality_ok": quality_ok,
        "health_ok": health_ok,
        "checks": checks,
        "reasons": [
            f"{check['label']}: {check['detail']}" if check["detail"] else check["label"]
            for check in checks
            if not check["ok"]
        ],
    }


def format_gate(result):
    lines = []
    for section, title in (("quality", "QUALITY"), ("suite health", "SUITE HEALTH")):
        lines.append(title)
        for check in result["checks"]:
            if check["section"] != section:
                continue
            mark = "PASS" if check["ok"] else "FAIL"
            line = f"  {mark}  {check['label']}"
            if check["detail"]:
                candidate = f"{line}: {check['detail']}"
                if len(candidate) <= 60:
                    lines.append(candidate)
                else:
                    lines.append(line)
                    lines.extend(textwrap.wrap(
                        check["detail"], width=62,
                        initial_indent="        ", subsequent_indent="        ",
                        break_on_hyphens=False, break_long_words=False,
                    ))
            else:
                lines.append(line)
        lines.append("")
    lines.append(f"RESULT: {'GREEN' if result['ok'] else 'RED'}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Benchmark report to gate")
    parser.add_argument("--manifest", type=Path, default=Path(__file__).parent / "manifest.json")
    parser.add_argument("--today", help="ISO date for an expiry drill")
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    today = date.fromisoformat(args.today) if args.today else date.today()
    result = check_gate(report, load_manifest(args.manifest), today)
    print(format_gate(result))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
