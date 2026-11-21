"""Offline tests for the pinned-cohort scoring rules."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import benchmark


def write_case(root, name, review_by="2026-12-12", scenario_id=None):
    path = root / f"{name}.json"
    path.write_text(json.dumps({
        "id": scenario_id or name,
        "validity": {
            "owner": "checkout on-call",
            "recorded_at": "2026-09-24",
            "review_by": review_by,
            "assumptions": {"topology": "checkout-db-pool-v1"},
        },
        "situation": {"alert": {}, "tool_responses": {}},
        "answer_key": {},
    }), encoding="utf-8")
    return path


def write_manifest(root, cases, coverage=("db_pool",), policy=None):
    path = root / "manifest.json"
    path.write_text(json.dumps({
        "cohort_id": "test-cohort",
        "created_at": "2026-09-24",
        "required_coverage": list(coverage),
        "policy": policy or {
            "min_attempts_per_case": 1,
            "min_pass_rate": 0.5,
            "max_ungraded_attempts": 0,
        },
        "cases": cases,
    }), encoding="utf-8")
    return path


class ClassifyTests(unittest.TestCase):
    def test_active_expired_and_historical_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_case(root, "active")
            write_case(root, "old", review_by="2026-01-01")
            write_case(root, "retired", review_by="2026-01-01")
            manifest = benchmark.load_manifest(write_manifest(root, [
                {"id": "active", "path": "active.json", "status": "active", "covers": "db_pool"},
                {"id": "old", "path": "old.json", "status": "active", "covers": "db_pool"},
                {"id": "retired", "path": "retired.json", "status": "historical", "covers": "db_pool",
                 "superseded_by": "active",
                 "retired": {"reason": "topology changed", "owner": "checkout on-call",
                             "reviewed_at": "2026-09-24"}},
            ]))
            cohort = benchmark.classify(manifest, date(2026, 11, 7))
            self.assertEqual([case.id for case in cohort.active], ["active"])
            self.assertEqual([case.id for case in cohort.expired], ["old"])
            self.assertEqual([case.id for case in cohort.historical], ["retired"])

    def test_historical_case_needs_a_review_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_case(root, "retired")
            with self.assertRaisesRegex(ValueError, "retired metadata"):
                benchmark.load_manifest(write_manifest(root, [
                    {"id": "retired", "path": "retired.json", "status": "historical",
                     "covers": "db_pool"},
                ]))

    def test_duplicate_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_case(root, "one")
            with self.assertRaisesRegex(ValueError, "duplicate case id"):
                benchmark.load_manifest(write_manifest(root, [
                    {"id": "one", "path": "one.json", "status": "active", "covers": "db_pool"},
                    {"id": "one", "path": "one.json", "status": "active", "covers": "db_pool"},
                ]))


class FingerprintTests(unittest.TestCase):
    def test_fingerprint_changes_with_case_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = write_case(root, "one")
            manifest = benchmark.load_manifest(write_manifest(root, [
                {"id": "one", "path": "one.json", "status": "active", "covers": "db_pool"},
            ]))
            before = benchmark.fingerprint(manifest)
            case.write_text(case.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            after = benchmark.fingerprint(benchmark.load_manifest(root / "manifest.json"))
            self.assertNotEqual(before, after)


class SummarizeTests(unittest.TestCase):
    def cohort(self, root):
        write_case(root, "one")
        write_case(root, "two")
        write_case(root, "old", review_by="2026-01-01")
        return benchmark.classify(benchmark.load_manifest(write_manifest(root, [
            {"id": "one", "path": "one.json", "status": "active", "covers": "db_pool"},
            {"id": "two", "path": "two.json", "status": "active", "covers": "db_pool"},
            {"id": "old", "path": "old.json", "status": "active", "covers": "db_pool"},
        ], coverage=("db_pool",))), date(2026, 11, 7))

    def test_only_active_attempts_are_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort = self.cohort(Path(tmp))
            report = benchmark.summarize(cohort, [
                {"case": "one", "status": "pass"},
                {"case": "one", "status": "fail"},
                {"case": "two", "status": "incomplete"},
            ], "2026-11-07")
            self.assertEqual(report["overall"]["passes"], 1)
            self.assertEqual(report["overall"]["attempts"], 3)
            self.assertEqual(report["overall"]["ungraded"], 1)
            self.assertEqual([entry["id"] for entry in report["expired"]], ["old"])
            self.assertEqual(report["per_case"][0]["pass_rate"], 0.5)

    def test_attempt_for_an_expired_case_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            cohort = self.cohort(Path(tmp))
            with self.assertRaisesRegex(ValueError, "not an active case"):
                benchmark.summarize(cohort, [{"case": "old", "status": "pass"}], "2026-11-07")

    def test_wilson_interval_contains_the_rate(self):
        low, high = benchmark.wilson(3, 3)
        self.assertLessEqual(low, 1.0)
        self.assertEqual(high, 1.0)
        self.assertGreater(low, 0.0)


class CompareTests(unittest.TestCase):
    def report(self, fingerprint_value, pass_rate, attempts=3):
        return {
            "cohort_id": "test-cohort",
            "cohort_fingerprint": fingerprint_value,
            "per_case": [{
                "case": "one", "attempts": attempts, "pass_rate": pass_rate,
                "ci_low": 0.2, "ci_high": 0.9,
            }],
            "overall": {
                "attempts": attempts, "pass_rate": pass_rate,
                "ci_low": 0.2, "ci_high": 0.9,
            },
        }

    def test_different_cohorts_cannot_be_compared(self):
        with self.assertRaisesRegex(ValueError, "cohorts differ"):
            benchmark.compare_reports(
                self.report("sha256:one", 0.5),
                self.report("sha256:two", 0.8),
            )

    def test_different_attempt_counts_cannot_be_compared(self):
        with self.assertRaisesRegex(ValueError, "different attempt counts"):
            benchmark.compare_reports(
                self.report("sha256:one", 0.5, attempts=2),
                self.report("sha256:one", 0.8, attempts=3),
            )

    def test_same_cohort_reports_a_delta(self):
        comparison = benchmark.compare_reports(
            self.report("sha256:one", 0.5),
            self.report("sha256:one", 0.67),
        )
        self.assertAlmostEqual(comparison["overall"]["delta"], 0.17, places=2)


if __name__ == "__main__":
    unittest.main()
