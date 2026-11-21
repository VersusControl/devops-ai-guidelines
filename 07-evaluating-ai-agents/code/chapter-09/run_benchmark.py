"""Run every active case N times and write one pinned benchmark report."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from answer_key import load_answer_key
from benchmark import (
    ATTEMPT_STATUSES,
    classify,
    format_report,
    load_manifest,
    summarize,
)
from config import load_settings
from jev_judge import call_cloudflare, evaluate
from run_agent import run_agent
from run_judge import DEMO_POLICY


HERE = Path(__file__).parent
MANIFEST = HERE / "manifest.json"
VARIANTS = HERE / "variants.json"
REPORTS = HERE / "reports"


def load_variant(name):
    variants = json.loads(VARIANTS.read_text(encoding="utf-8"))
    if name not in variants:
        raise ValueError(f"unknown variant: {name}")
    variant = variants[name]
    if not isinstance(variant.get("instructions"), str) or not variant["instructions"].strip():
        raise ValueError(f"{name}: instructions must be nonempty text")
    if type(variant.get("max_steps")) is not int or not 1 <= variant["max_steps"] <= 8:
        raise ValueError(f"{name}: max_steps must be an integer from 1 to 8")
    return variant


def load_replay(path, cohort, runs):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    labels = {"variant", "variant_description", "agent_model", "attempts"}
    if not labels <= raw.keys() or not isinstance(raw["attempts"], dict):
        raise ValueError("replay file is incomplete")
    if raw.get("replay") is not True:
        raise ValueError("replay file must declare \"replay\": true")
    records = []
    for case in cohort.active:
        entries = raw["attempts"].get(case.id)
        if not isinstance(entries, list) or len(entries) != runs:
            raise ValueError(f"{case.id}: replay needs exactly {runs} attempts")
        for number, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict) or entry.get("status") not in ATTEMPT_STATUSES:
                raise ValueError(f"{case.id} attempt {number}: invalid status")
            if entry["status"] == "pass":
                gates = entry.get("hard_gates")
                judge = entry.get("jev")
                if not (isinstance(gates, dict)
                        and set(gates) == {"cause", "evidence", "distraction", "steps"}
                        and all(value is True for value in gates.values())
                        and isinstance(judge, dict)
                        and judge.get("explanation_score", 0) >= 1.5
                        and judge.get("unsupported_claim", 1) <= 0.2):
                    raise ValueError(f"{case.id} attempt {number}: pass is not a complete pass")
            if entry["status"] in {"incomplete", "error"} and not (
                entry.get("judge_reason") or entry.get("error_type")
            ):
                raise ValueError(f"{case.id} attempt {number}: ungraded attempt needs a reason")
            records.append({
                "case": case.id,
                "covers": case.covers,
                "attempt": number,
                **entry,
            })
    return raw, records


def run_attempt(manifest, case, settings, variant, attempt):
    record = {"case": case.id, "covers": case.covers, "attempt": attempt, "status": "error"}
    try:
        case_path = manifest.base_dir / case.path
        agent_input, conclusion = run_agent(
            settings,
            case_path=case_path,
            instructions=variant["instructions"],
            max_steps=variant["max_steps"],
        )
        answer = load_answer_key(case_path)
        if agent_input.scenario_id != answer.scenario_id:
            raise ValueError("answer belongs to another case")
        result = evaluate(
            conclusion,
            answer,
            lambda payload: call_cloudflare(payload, settings),
            DEMO_POLICY,
        )
        record.update({
            "status": result["status"],
            "hard_gates": result["hard"]["gates"],
            "hard_passed": result["hard"]["passed"],
            "category": conclusion.category,
            "cause_change": conclusion.cause_change,
            "cause_effect": conclusion.cause_effect,
            "tool_calls": [
                step["tool"] for step in conclusion.trajectory
                if step["type"] == "call_tool"
            ],
            "steps": len(conclusion.trajectory),
        })
        if "reason" in result:
            record["judge_reason"] = result["reason"]
        if "judge" in result:
            record["jev"] = {
                "model": result["judge"]["model"],
                "rubric": result["judge"]["rubric"],
                "explanation_score": result["judge"]["quality"]["score"],
                "confidence": result["judge"]["quality"]["confidence"],
                "unsupported_claim": result["judge"]["unsupported"]["noul"],
            }
    except Exception as error:
        record["error_type"] = type(error).__name__
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=["baseline", "candidate"], default="baseline")
    parser.add_argument("--runs", type=int, default=3, help="Attempts per active case, from 1 to 5")
    parser.add_argument("--report", type=Path, help="Where to write the report")
    parser.add_argument("--replay", type=Path, help="Score a recorded attempt file without model calls")
    parser.add_argument("--today", help="ISO date for an expiry drill")
    args = parser.parse_args()
    if not 1 <= args.runs <= 5:
        parser.error("--runs must be between 1 and 5")
    today = date.fromisoformat(args.today) if args.today else date.today()
    manifest = load_manifest(MANIFEST)
    cohort = classify(manifest, today)

    print(f"Cohort: {manifest.cohort_id}")
    print(f"Active: {', '.join(c.id for c in cohort.active) or 'none'}")
    print(f"Expired, not scored: {', '.join(c.id for c in cohort.expired) or 'none'}")
    print(f"Historical, not scored: {', '.join(c.id for c in cohort.historical) or 'none'}")

    if args.replay:
        replay, records = load_replay(args.replay, cohort, args.runs)
        variant_name = replay["variant"]
        variant_description = replay["variant_description"]
        agent_model = replay["agent_model"]
        print(f"Variant: {variant_name} — {variant_description}")
        print("Source: recorded replay (no model calls)")
    else:
        variant = load_variant(args.variant)
        variant_name = args.variant
        variant_description = variant["description"]
        settings = load_settings(require_jev=True)
        agent_model = settings.openai_model
        print(f"Variant: {variant_name} — {variant_description}")
        tasks = [
            (case, attempt)
            for case in cohort.active
            for attempt in range(1, args.runs + 1)
        ]
        with ThreadPoolExecutor(max_workers=min(6, len(tasks) or 1)) as pool:
            records = list(pool.map(
                lambda task: run_attempt(manifest, task[0], settings, variant, task[1]),
                tasks,
            ))

    report = summarize(cohort, records, today.isoformat())
    report.update({
        "variant": variant_name,
        "variant_description": variant_description,
        "agent_model": agent_model,
        "replay": bool(args.replay),
        "attempts": records,
    })
    report_path = args.report or REPORTS / f"benchmark-{variant_name}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print()
    print(format_report(report))
    print(f"\nFull run record: {report_path}")
    overall = report["overall"]
    if cohort.expired:
        print("Benchmark is unhealthy: an active case passed its review date.")
    if overall["ungraded"]:
        print(f"Benchmark is unhealthy: {overall['ungraded']} attempts have no complete grade.")
    if cohort.expired or overall["ungraded"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
