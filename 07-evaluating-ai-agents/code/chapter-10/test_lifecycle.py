"""Offline tests for case capture, registration, and retirement."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from case_lifecycle import register_case, retire_case, validate_draft


TODAY = date(2026, 11, 7)


def case_body(case_id, review_by="2027-02-07"):
    return {
        "id": case_id,
        "validity": {
            "owner": "checkout on-call",
            "recorded_at": "2026-11-06",
            "review_by": review_by,
            "assumptions": {"topology": "checkout-db-pool-v1"},
            "source": {
                "kind": "production_miss",
                "reference": "misses/run.json",
                "observed_at": "2026-11-06",
            },
        },
        "situation": {
            "alert": {
                "service": "checkout-service",
                "message": "checkout-service p95 latency > 2s",
                "started_at": "15:10",
            },
            "tool_responses": {
                "get_deploys": {
                    "service": "checkout-service",
                    "deploys": [{"at": "15:08", "change": "CACHE_TTL 300 -> 0",
                                 "commit": "c4a1b2c", "author": "release"}],
                },
                "get_logs": {
                    "service": "checkout-service",
                    "lines": [
                        "15:09:02 WARN cache miss ratio 0.98",
                        "15:14:22 INFO payment-provider latency 900ms (was 90ms)",
                    ],
                },
            },
        },
        "answer_key": {
            "true_category": "deploy",
            "true_cause": "A deploy set CACHE_TTL to 0 and caused a cache stampede.",
            "cause_change": "CACHE_TTL 300 -> 0",
            "cause_effect": "cache_stampede",
            "required_evidence": ["get_deploys", "get_logs"],
            "distraction": "payment-provider latency rose after the alert",
            "distraction_source": "get_logs",
            "distraction_marker": "payment-provider",
            "distraction_id": "payment_provider",
            "max_steps": 3,
        },
    }


def seed_case():
    return {
        "id": "seed-case",
        "validity": {
            "owner": "checkout on-call",
            "recorded_at": "2026-09-24",
            "review_by": "2027-12-12",
            "assumptions": {"topology": "checkout-db-pool-v1"},
        },
        "situation": {"alert": {}, "tool_responses": {}},
        "answer_key": {},
    }


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "scenarios").mkdir()
        (self.root / "inbox").mkdir()
        (self.root / "misses").mkdir()
        (self.root / "misses" / "run.json").write_text("{}", encoding="utf-8")
        (self.root / "scenarios" / "seed.json").write_text(
            json.dumps(seed_case()), encoding="utf-8")
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(json.dumps({
            "cohort_id": "test",
            "created_at": "2026-09-24",
            "required_coverage": ["db_pool"],
            "policy": {"min_attempts_per_case": 1, "min_pass_rate": 0.5,
                       "max_ungraded_attempts": 0},
            "cases": [{"id": "seed", "path": "scenarios/seed.json",
                       "status": "active", "covers": "db_pool"}],
        }), encoding="utf-8")
        self.draft = self.root / "inbox" / "cache.json"
        self.draft.write_text(json.dumps(case_body("checkout-cache-stampede")),
                              encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_draft_registers_and_adds_coverage(self):
        result = register_case(self.manifest, self.draft, "cache_stampede",
                               apply=True, today=TODAY)
        self.assertFalse(result["dry_run"])
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertIn("cache_stampede", manifest["required_coverage"])
        self.assertEqual(manifest["cases"][-1]["id"], "checkout-cache-stampede")
        self.assertTrue((self.root / "scenarios" / "cache.json").is_file())

    def test_dry_run_leaves_the_manifest_alone(self):
        before = self.manifest.read_text(encoding="utf-8")
        result = register_case(self.manifest, self.draft, "cache_stampede",
                               apply=False, today=TODAY)
        self.assertTrue(result["dry_run"])
        self.assertEqual(self.manifest.read_text(encoding="utf-8"), before)
        self.assertFalse((self.root / "scenarios" / "cache.json").exists())

    def test_duplicate_case_is_rejected(self):
        register_case(self.manifest, self.draft, "cache_stampede", apply=True, today=TODAY)
        with self.assertRaisesRegex(ValueError, "already in the cohort"):
            register_case(self.manifest, self.draft, "cache_stampede", apply=True, today=TODAY)

    def test_past_review_date_is_rejected(self):
        draft = case_body("expired-draft", review_by="2026-11-07")
        self.draft.write_text(json.dumps(draft), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "after today"):
            validate_draft(self.draft, TODAY)

    def test_missing_miss_record_is_rejected(self):
        draft = case_body("no-source")
        draft["validity"]["source"]["reference"] = "misses/absent.json"
        self.draft.write_text(json.dumps(draft), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "reference is missing"):
            register_case(self.manifest, self.draft, "cache_stampede", apply=True, today=TODAY)

    def test_unseen_distraction_is_rejected(self):
        draft = case_body("early-distraction")
        draft["situation"]["tool_responses"]["get_logs"]["lines"][1] = (
            "15:09:22 INFO payment-provider latency 900ms (was 90ms)")
        self.draft.write_text(json.dumps(draft), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "after the alert"):
            validate_draft(self.draft, TODAY)

    def test_retired_case_keeps_its_review_record(self):
        register_case(self.manifest, self.draft, "cache_stampede", apply=True, today=TODAY)
        result = retire_case(
            self.manifest, "seed", "Topology changed", "checkout on-call",
            replaced_by="checkout-cache-stampede", apply=True, today=TODAY,
        )
        self.assertEqual(result["case"]["status"], "historical")
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        retired = next(case for case in manifest["cases"] if case["id"] == "seed")
        self.assertEqual(retired["retired"]["reason"], "Topology changed")
        self.assertEqual(retired["superseded_by"], "checkout-cache-stampede")
        self.assertTrue((self.root / "scenarios" / "seed.json").is_file())

    def test_replacement_must_be_active(self):
        with self.assertRaisesRegex(ValueError, "not active"):
            retire_case(self.manifest, "seed", "Old", "checkout on-call",
                        replaced_by="missing", apply=True, today=TODAY)

    def test_retiring_twice_is_rejected(self):
        retire_case(self.manifest, "seed", "Old", "checkout on-call",
                    apply=True, today=TODAY)
        with self.assertRaisesRegex(ValueError, "not an active case"):
            retire_case(self.manifest, "seed", "Old again", "checkout on-call",
                        apply=True, today=TODAY)


if __name__ == "__main__":
    unittest.main()
