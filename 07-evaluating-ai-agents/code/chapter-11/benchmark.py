"""Score a pinned cohort and keep expired and historical cases out of the number."""

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ATTEMPT_STATUSES = {"pass", "fail", "review_needed", "incomplete", "error"}
UNGRADED_STATUSES = {"incomplete", "error"}
CASE_STATUSES = {"active", "historical"}


@dataclass(frozen=True)
class Case:
    id: str
    path: str
    status: str
    covers: str
    superseded_by: str = ""
    retired: dict = None


@dataclass(frozen=True)
class Manifest:
    cohort_id: str
    created_at: str
    required_coverage: tuple
    policy: dict
    cases: tuple
    base_dir: Path = None


@dataclass(frozen=True)
class Expired:
    id: str
    review_by: date


@dataclass(frozen=True)
class Cohort:
    cohort_id: str
    fingerprint: str
    active: tuple
    expired: tuple
    historical: tuple


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def load_manifest(path):
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(raw, dict), "manifest must be an object")
    _require(isinstance(raw.get("cohort_id"), str) and raw["cohort_id"].strip(),
             "cohort_id must be nonempty text")
    _require(isinstance(raw.get("created_at"), str) and raw["created_at"].strip(),
             "created_at must be nonempty text")
    coverage = raw.get("required_coverage")
    _require(isinstance(coverage, list) and coverage
             and all(isinstance(name, str) and name for name in coverage),
             "required_coverage must be a nonempty list of names")
    _require(len(set(coverage)) == len(coverage), "required_coverage has duplicates")
    policy = raw.get("policy")
    _require(isinstance(policy, dict), "policy must be an object")
    _require(isinstance(policy.get("min_attempts_per_case"), int)
             and policy["min_attempts_per_case"] >= 1,
             "policy.min_attempts_per_case must be a positive integer")
    _require(isinstance(policy.get("min_pass_rate"), (int, float))
             and 0 <= policy["min_pass_rate"] <= 1,
             "policy.min_pass_rate must be between 0 and 1")
    _require(isinstance(policy.get("max_ungraded_attempts"), int)
             and policy["max_ungraded_attempts"] >= 0,
             "policy.max_ungraded_attempts must be a nonnegative integer")
    min_case_pass_rate = policy.get("min_case_pass_rate", 0.0)
    _require(isinstance(min_case_pass_rate, (int, float))
             and 0 <= min_case_pass_rate <= 1,
             "policy.min_case_pass_rate must be between 0 and 1")
    max_retirement_age_days = policy.get("max_retirement_age_days", 365)
    _require(isinstance(max_retirement_age_days, int) and max_retirement_age_days >= 1,
             "policy.max_retirement_age_days must be a positive integer")
    policy = {
        **policy,
        "min_case_pass_rate": min_case_pass_rate,
        "max_retirement_age_days": max_retirement_age_days,
    }
    cases = raw.get("cases")
    _require(isinstance(cases, list) and cases, "cases must be a nonempty list")
    parsed = []
    seen = set()
    base_dir = path.parent
    for entry in cases:
        _require(isinstance(entry, dict), "each case must be an object")
        case_id = entry.get("id")
        _require(isinstance(case_id, str) and case_id, "each case needs an id")
        _require(case_id not in seen, f"duplicate case id: {case_id}")
        seen.add(case_id)
        _require(isinstance(entry.get("path"), str) and entry["path"],
                 f"{case_id}: path must be nonempty text")
        _require(entry.get("status") in CASE_STATUSES, f"{case_id}: invalid status")
        _require(isinstance(entry.get("covers"), str) and entry["covers"],
                 f"{case_id}: covers must be nonempty text")
        _require((base_dir / entry["path"]).is_file(), f"{case_id}: case file is missing")
        retired = entry.get("retired")
        if entry["status"] == "historical":
            _require(isinstance(retired, dict), f"{case_id}: historical case needs retired metadata")
            _require(isinstance(retired.get("reason"), str) and retired["reason"].strip(),
                     f"{case_id}: retired.reason must be nonempty")
            _require(isinstance(retired.get("owner"), str) and retired["owner"].strip(),
                     f"{case_id}: retired.owner must be nonempty")
            _require(isinstance(retired.get("reviewed_at"), str) and retired["reviewed_at"].strip(),
                     f"{case_id}: retired.reviewed_at must be nonempty")
            date.fromisoformat(retired["reviewed_at"])
        else:
            _require(retired is None, f"{case_id}: only historical cases carry retired metadata")
            _require(not entry.get("superseded_by"), f"{case_id}: active case cannot be superseded")
        parsed.append(Case(
            id=case_id,
            path=entry["path"],
            status=entry["status"],
            covers=entry["covers"],
            superseded_by=entry.get("superseded_by", ""),
            retired=retired,
        ))
    _require(len({case.covers for case in parsed if case.status == "active"})
             <= len(coverage), "a case covers a label that is not required")
    return Manifest(
        cohort_id=raw["cohort_id"],
        created_at=raw["created_at"],
        required_coverage=tuple(coverage),
        policy=policy,
        cases=tuple(parsed),
        base_dir=base_dir,
    )


def case_review_by(manifest, case):
    raw = json.loads((manifest.base_dir / case.path).read_text(encoding="utf-8"))
    try:
        review_by = raw["validity"]["review_by"]
        assumptions = raw["validity"]["assumptions"]
    except (KeyError, TypeError):
        raise ValueError(f"{case.id}: validity metadata is incomplete") from None
    _require(isinstance(assumptions, dict) and assumptions,
             f"{case.id}: validity.assumptions must not be empty")
    return date.fromisoformat(review_by)


def fingerprint(manifest):
    digest = hashlib.sha256()
    digest.update(manifest.cohort_id.encode("utf-8"))
    for case in manifest.cases:
        body = (manifest.base_dir / case.path).read_bytes()
        digest.update(b"\0")
        digest.update(case.id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(case.status.encode("utf-8"))
        digest.update(b"\0")
        digest.update(case.covers.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(body).digest())
    return "sha256:" + digest.hexdigest()


def classify(manifest, today=None):
    today = today or date.today()
    active, expired, historical = [], [], []
    for case in manifest.cases:
        if case.status == "historical":
            historical.append(case)
            continue
        review_by = case_review_by(manifest, case)
        if today > review_by:
            expired.append(Expired(id=case.id, review_by=review_by))
        else:
            active.append(case)
    return Cohort(
        cohort_id=manifest.cohort_id,
        fingerprint=fingerprint(manifest),
        active=tuple(active),
        expired=tuple(expired),
        historical=tuple(historical),
    )


def wilson(successes, attempts, z=1.96):
    if attempts == 0:
        return 0.0, 1.0
    p = successes / attempts
    denominator = 1 + z * z / attempts
    center = (p + z * z / (2 * attempts)) / denominator
    half = z * math.sqrt(p * (1 - p) / attempts + z * z / (4 * attempts * attempts)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def summarize(cohort, attempts, as_of):
    active_ids = {case.id for case in cohort.active}
    for attempt in attempts:
        _require(isinstance(attempt, dict) and "case" in attempt,
                 "every attempt needs a case id")
        _require(attempt["case"] in active_ids,
                 f"attempt for {attempt['case']} is not an active case")
        _require(attempt.get("status") in ATTEMPT_STATUSES,
                 f"{attempt['case']}: invalid attempt status")
    per_case = []
    for case in cohort.active:
        case_attempts = [a for a in attempts if a["case"] == case.id]
        passes = sum(a["status"] == "pass" for a in case_attempts)
        ungraded = sum(a["status"] in UNGRADED_STATUSES for a in case_attempts)
        low, high = wilson(passes, len(case_attempts))
        per_case.append({
            "case": case.id,
            "covers": case.covers,
            "attempts": len(case_attempts),
            "passes": passes,
            "fails": sum(a["status"] == "fail" for a in case_attempts),
            "review_needed": sum(a["status"] == "review_needed" for a in case_attempts),
            "incomplete": sum(a["status"] == "incomplete" for a in case_attempts),
            "errors": sum(a["status"] == "error" for a in case_attempts),
            "ungraded": ungraded,
            "pass_rate": passes / len(case_attempts) if case_attempts else 0.0,
            "ci_low": low,
            "ci_high": high,
        })
    total = len(attempts)
    passes = sum(a["status"] == "pass" for a in attempts)
    low, high = wilson(passes, total)
    return {
        "as_of": as_of,
        "cohort_id": cohort.cohort_id,
        "cohort_fingerprint": cohort.fingerprint,
        "attempts_per_case": max((entry["attempts"] for entry in per_case), default=0),
        "active": [case.id for case in cohort.active],
        "expired": [
            {"id": entry.id, "review_by": entry.review_by.isoformat()}
            for entry in cohort.expired
        ],
        "historical": [
            {"id": case.id, "superseded_by": case.superseded_by, "reason": case.retired["reason"]}
            for case in cohort.historical
        ],
        "per_case": per_case,
        "overall": {
            "attempts": total,
            "passes": passes,
            "pass_rate": passes / total if total else 0.0,
            "ci_low": low,
            "ci_high": high,
            "ungraded": sum(a["status"] in UNGRADED_STATUSES for a in attempts),
            "review_needed": sum(a["status"] == "review_needed" for a in attempts),
        },
    }


def compare_reports(baseline, candidate):
    _require(baseline.get("cohort_fingerprint") == candidate.get("cohort_fingerprint"),
             "cohorts differ; re-run both variants on the same pinned set")
    _require(baseline.get("cohort_id") == candidate.get("cohort_id"),
             "cohort ids differ")
    baseline_cases = {entry["case"]: entry for entry in baseline["per_case"]}
    candidate_cases = {entry["case"]: entry for entry in candidate["per_case"]}
    _require(set(baseline_cases) == set(candidate_cases),
             "reports scored different active cases")
    rows = []
    for case_id in [entry["case"] for entry in baseline["per_case"]]:
        before, after = baseline_cases[case_id], candidate_cases[case_id]
        _require(before["attempts"] == after["attempts"],
                 f"{case_id}: reports use different attempt counts")
        rows.append({
            "case": case_id,
            "attempts": before["attempts"],
            "baseline_rate": before["pass_rate"],
            "candidate_rate": after["pass_rate"],
            "delta": after["pass_rate"] - before["pass_rate"],
            "baseline_ci": (before["ci_low"], before["ci_high"]),
            "candidate_ci": (after["ci_low"], after["ci_high"]),
            "intervals_overlap": not (
                after["ci_low"] > before["ci_high"] or before["ci_low"] > after["ci_high"]
            ),
        })
    before, after = baseline["overall"], candidate["overall"]
    _require(before["attempts"] == after["attempts"],
             "reports use different total attempt counts")
    return {
        "baseline": baseline.get("variant", "baseline"),
        "candidate": candidate.get("variant", "candidate"),
        "overall": {
            "attempts": before["attempts"],
            "baseline_rate": before["pass_rate"],
            "candidate_rate": after["pass_rate"],
            "delta": after["pass_rate"] - before["pass_rate"],
            "baseline_ci": (before["ci_low"], before["ci_high"]),
            "candidate_ci": (after["ci_low"], after["ci_high"]),
            "intervals_overlap": not (
                after["ci_low"] > before["ci_high"] or before["ci_low"] > after["ci_high"]
            ),
        },
        "per_case": rows,
    }


def format_report(report):
    lines = [
        f"Cohort: {report['cohort_id']}",
        f"Fingerprint: {report['cohort_fingerprint'][:19]}…",
        f"Variant: {report.get('variant', '?')}",
        f"Attempts per case: {report['attempts_per_case']}",
        "",
        f"{'case':<26}{'att':<5}{'pass':<6}{'rate':<7}{'95% CI':<11}ungraded",
    ]
    for entry in report["per_case"]:
        interval = f"[{entry['ci_low']:.0%},{entry['ci_high']:.0%}]"
        lines.append(
            f"{entry['case']:<26}{entry['attempts']:<5}{entry['passes']:<6}"
            f"{entry['pass_rate']:<7.0%}{interval:<11}{entry['ungraded']}"
        )
    overall = report["overall"]
    lines.extend([
        "",
        f"Overall: {overall['passes']}/{overall['attempts']} passes "
        f"({overall['pass_rate']:.0%}, 95% CI [{overall['ci_low']:.0%}, {overall['ci_high']:.0%}])",
        f"Expired (not scored): {', '.join(e['id'] for e in report['expired']) or 'none'}",
        f"Historical (not scored): {', '.join(h['id'] for h in report['historical']) or 'none'}",
    ])
    return "\n".join(lines)


def format_comparison(comparison):
    overall = comparison["overall"]
    lines = [
        f"Baseline:  {comparison['baseline']}",
        f"Candidate: {comparison['candidate']}",
        "",
        f"{'case':<26}{'base':<6}{'cand':<6}{'delta':<7}CI",
    ]
    for row in comparison["per_case"]:
        lines.append(
            f"{row['case']:<26}{row['baseline_rate']:<6.0%}"
            f"{row['candidate_rate']:<6.0%}{row['delta']:+7.0%} "
            f"{'overlap' if row['intervals_overlap'] else 'separate'}"
        )
    lines.extend([
        "",
        f"Overall: {overall['baseline_rate']:.0%} -> {overall['candidate_rate']:.0%} "
        f"({overall['delta']:+.0%}), CI "
        f"{'overlap' if overall['intervals_overlap'] else 'separate'}",
    ])
    return "\n".join(lines)
