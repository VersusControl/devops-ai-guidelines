"""Offline tests for the quality and suite-health gate."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from benchmark import classify, load_manifest
from gate import check_gate


TODAY = date(2026, 11, 7)


def write_case(root, name, review_by="2027-02-07"):
    (root / f"{name}.json").write_text(json.dumps({
        "id": name,
        "validity": {
            "owner": "checkout on-call",
            "recorded_at": "2026-09-24",
            "review_by": review_by,
            "assumptions": {"topology": "checkout-db-pool-v1"},
        },
        "situation": {"alert": {}, "tool_responses": {}},
        "answer_key": {},
    }), encoding="utf-8")


def write_manifest(root, cases, coverage, policy=None):
    path = root / "manifest.json"
    path.write_text(json.dumps({
        "cohort_id": "gate-test",
        "created_at": "2026-09-24",
        "required_coverage": coverage,
        "policy": policy or {
            "min_attempts_per_case": 3,
            "min_pass_rate": 0.8,
            "min_case_pass_rate": 0.5,
            "max_ungraded_attempts": 0,
            "max_retirement_age_days": 365,
        },
        "cases": cases,
    }), encoding="utf-8")
    return path


def report_for(cohort, rates, attempts=3, ungraded_case=None):
    per_case = []
    total = 0
    passes = 0
    ungraded = 0
    for case in cohort.active:
        case_passes = rates.get(case.id, 0)
        case_ungraded = attempts if ungraded_case == case.id else 0
        per_case.append({
            "case": case.id,
            "covers": case.covers,
            "attempts": attempts,
            "passes": case_passes,
            "ungraded": case_ungraded,
            "pass_rate": case_passes / attempts,
        })
        total += attempts
        passes += case_passes
        ungraded += case_ungraded
    return {
        "cohort_id": cohort.cohort_id,
        "cohort_fingerprint": cohort.fingerprint,
        "active": [case.id for case in cohort.active],
        "per_case": per_case,
        "overall": {
            "attempts": total,
            "passes": passes,
            "pass_rate": passes / total,
            "ungraded": ungraded,
        },
    }


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write_case(self.root, "pool")
        write_case(self.root, "dependency")
        self.manifest_path = write_manifest(self.root, [
            {"id": "pool", "path": "pool.json", "status": "active", "covers": "db_pool"},
            {"id": "dependency", "path": "dependency.json", "status": "active",
             "covers": "payment_dependency"},
        ], ["db_pool", "payment_dependency"])
        self.manifest = load_manifest(self.manifest_path)
        self.cohort = classify(self.manifest, TODAY)

    def tearDown(self):
        self.tmp.cleanup()

    def test_green_when_quality_and_suite_are_healthy(self):
        result = check_gate(
            report_for(self.cohort, {"pool": 3, "dependency": 2}),
            self.manifest,
            TODAY,
        )
        self.assertTrue(result["ok"], result["reasons"])
        self.assertTrue(result["quality_ok"])
        self.assertTrue(result["health_ok"])

    def test_low_overall_rate_fails_quality(self):
        result = check_gate(
            report_for(self.cohort, {"pool": 2, "dependency": 1}),
            self.manifest,
            TODAY,
        )
        self.assertFalse(result["quality_ok"])
        self.assertTrue(result["health_ok"])
        self.assertTrue(any("overall pass rate" in reason for reason in result["reasons"]))

    def test_one_weak_case_fails_the_floor(self):
        result = check_gate(
            report_for(self.cohort, {"pool": 3, "dependency": 0}),
            self.manifest,
            TODAY,
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("floor" in reason for reason in result["reasons"]))

    def test_ungraded_attempt_fails_quality(self):
        result = check_gate(
            report_for(self.cohort, {"pool": 3, "dependency": 3}, ungraded_case="pool"),
            self.manifest,
            TODAY,
        )
        self.assertFalse(result["quality_ok"])
        self.assertTrue(any("ungraded" in reason for reason in result["reasons"]))

    def test_a_new_manifest_fingerprint_cannot_reuse_an_old_report(self):
        report = report_for(self.cohort, {"pool": 3, "dependency": 3})
        write_case(self.root, "dependency", review_by="2027-03-01")
        result = check_gate(report, load_manifest(self.manifest_path), TODAY)
        self.assertFalse(result["quality_ok"])
        self.assertTrue(any("cohort fingerprint" in reason for reason in result["reasons"]))

    def test_report_missing_an_active_case_fails(self):
        report = report_for(self.cohort, {"pool": 3, "dependency": 3})
        report["per_case"] = report["per_case"][:1]
        result = check_gate(report, self.manifest, TODAY)
        self.assertFalse(result["quality_ok"])
        self.assertTrue(any("every active case" in reason for reason in result["reasons"]))

    def test_expired_active_case_fails_suite_health(self):
        write_case(self.root, "pool", review_by="2026-10-01")
        result = check_gate(
            report_for(self.cohort, {"pool": 3, "dependency": 3}),
            load_manifest(self.manifest_path),
            TODAY,
        )
        self.assertFalse(result["health_ok"])
        self.assertTrue(any("expired active cases" in reason for reason in result["reasons"]))

    def test_coverage_gap_fails_suite_health(self):
        manifest = load_manifest(write_manifest(self.root, [
            {"id": "pool", "path": "pool.json", "status": "active", "covers": "db_pool"},
        ], ["db_pool", "payment_dependency"]))
        cohort = classify(manifest, TODAY)
        result = check_gate(report_for(cohort, {"pool": 3}), manifest, TODAY)
        self.assertFalse(result["health_ok"])
        self.assertTrue(any("coverage" in reason for reason in result["reasons"]))

    def test_stale_exclusion_fails_suite_health(self):
        write_case(self.root, "old", review_by="2025-01-01")
        manifest = load_manifest(write_manifest(self.root, [
            {"id": "pool", "path": "pool.json", "status": "active", "covers": "db_pool"},
            {"id": "old", "path": "old.json", "status": "historical", "covers": "db_pool",
             "retired": {"reason": "old topology", "owner": "checkout on-call",
                         "reviewed_at": "2024-01-01"}},
        ], ["db_pool"]))
        cohort = classify(manifest, TODAY)
        result = check_gate(report_for(cohort, {"pool": 3}), manifest, TODAY)
        self.assertFalse(result["health_ok"])
        self.assertTrue(any("exclusion" in reason for reason in result["reasons"]))


if __name__ == "__main__":
    unittest.main()
