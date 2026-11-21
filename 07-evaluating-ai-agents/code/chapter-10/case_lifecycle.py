"""Validate, register, and retire cases without losing their review history."""

import json
import re
import shutil
from datetime import date, time
from pathlib import Path

from answer_key import load_answer_key
from benchmark import load_manifest


CASE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOURCE_KINDS = {"production_miss", "drill", "synthetic"}
REQUIRED_ANSWER_FIELDS = {
    "true_category", "true_cause", "cause_change", "cause_effect",
    "required_evidence", "distraction", "distraction_source",
    "distraction_marker", "distraction_id", "max_steps",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_draft(path, today=None):
    today = today or date.today()
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    case_id = raw.get("id")
    _require(isinstance(case_id, str) and CASE_ID.fullmatch(case_id),
             "id must be kebab-case, such as checkout-cache-stampede")
    validity = raw.get("validity")
    _require(isinstance(validity, dict), "validity must be an object")
    _require(isinstance(validity.get("owner"), str) and validity["owner"].strip(),
             "validity.owner must name a person or team")
    _require(isinstance(validity.get("assumptions"), dict) and validity["assumptions"],
             "validity.assumptions must not be empty")
    try:
        recorded_at = date.fromisoformat(validity["recorded_at"])
        review_by = date.fromisoformat(validity["review_by"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("validity.recorded_at and review_by must be ISO dates") from None
    _require(recorded_at <= today, "validity.recorded_at cannot be in the future")
    _require(review_by > today, "validity.review_by must be after today")
    source = validity.get("source")
    _require(isinstance(source, dict), "validity.source must record where the case came from")
    _require(source.get("kind") in SOURCE_KINDS, "validity.source.kind is not reviewed")
    _require(isinstance(source.get("reference"), str) and source["reference"].strip(),
             "validity.source.reference must point at the run or note")
    _require(isinstance(source.get("observed_at"), str) and source["observed_at"].strip(),
             "validity.source.observed_at must record when the miss happened")

    situation = raw.get("situation")
    _require(isinstance(situation, dict), "situation must be an object")
    alert = situation.get("alert")
    _require(isinstance(alert, dict), "situation.alert must be an object")
    for field in ("service", "message", "started_at"):
        _require(isinstance(alert.get(field), str) and alert[field].strip(),
                 f"situation.alert.{field} must be nonempty")
    try:
        alert_time = time.fromisoformat(alert["started_at"])
    except ValueError:
        raise ValueError("situation.alert.started_at must be HH:MM or HH:MM:SS") from None
    responses = situation.get("tool_responses")
    _require(isinstance(responses, dict) and responses,
             "situation.tool_responses must not be empty")

    answer = load_answer_key(path)
    _require(set(REQUIRED_ANSWER_FIELDS) <= set(raw["answer_key"]),
             "answer_key is incomplete")
    _require(answer.max_steps >= len(answer.required_evidence) + 1,
             "answer_key.max_steps cannot fit the required evidence and a conclusion")
    _require(set(answer.required_evidence) <= set(responses),
             "required evidence names a tool with no recorded response")
    _require(answer.distraction_source in responses,
             "distraction_source has no recorded response")
    lines = responses[answer.distraction_source].get("lines", [])
    _require(any(
        answer.distraction_marker in line
        and _line_time(line) is not None
        and _line_time(line) > alert_time
        for line in lines
    ), "distraction marker must appear after the alert in the recorded lines")
    for name, response in responses.items():
        if "raises" not in response:
            _require(response.get("service") == alert["service"],
                     f"{name}: recorded service does not match the alert")
    return {
        "id": case_id,
        "owner": validity["owner"],
        "review_by": review_by.isoformat(),
        "source": source["kind"],
    }


def _line_time(line):
    try:
        return time.fromisoformat(line[:8])
    except (ValueError, TypeError):
        return None


def _read_manifest(path):
    path = Path(path)
    return path, json.loads(path.read_text(encoding="utf-8"))


def _write(path, manifest):
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    load_manifest(path)


def register_case(manifest_path, draft_path, covers, apply=False, today=None):
    today = today or date.today()
    summary = validate_draft(draft_path, today)
    manifest_path, manifest = _read_manifest(manifest_path)
    base_dir = manifest_path.parent
    draft_raw = json.loads(Path(draft_path).read_text(encoding="utf-8"))
    reference = Path(draft_raw["validity"]["source"]["reference"])
    reference_path = reference if reference.is_absolute() else base_dir / reference
    _require(reference_path.is_file(),
             f"validity.source.reference is missing: {reference}")
    _require(isinstance(covers, str) and covers.strip(), "covers must be nonempty")
    _require(all(case.get("id") != summary["id"] for case in manifest["cases"]),
             f"{summary['id']} is already in the cohort")
    draft_path = Path(draft_path)
    target = base_dir / "scenarios" / draft_path.name
    if target != draft_path:
        _require(not target.exists() or target.read_bytes() == draft_path.read_bytes(),
                 f"{target} already exists with different content")
    entry = {
        "id": summary["id"],
        "path": target.relative_to(base_dir).as_posix(),
        "status": "active",
        "covers": covers,
    }
    manifest["cases"].append(entry)
    if covers not in manifest["required_coverage"]:
        manifest["required_coverage"].append(covers)
    if not apply:
        return {"action": "register", "case": entry, "dry_run": True}
    created = False
    original = manifest_path.read_text(encoding="utf-8")
    try:
        if target != draft_path:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(draft_path, target)
            created = True
        _write(manifest_path, manifest)
    except Exception:
        manifest_path.write_text(original, encoding="utf-8")
        if created:
            target.unlink()
        raise
    return {"action": "register", "case": entry, "dry_run": False}


def retire_case(manifest_path, case_id, reason, owner, replaced_by="", apply=False,
                today=None):
    today = today or date.today()
    manifest_path, manifest = _read_manifest(manifest_path)
    _require(isinstance(reason, str) and reason.strip(), "retire reason must be nonempty")
    _require(isinstance(owner, str) and owner.strip(), "retire owner must be nonempty")
    active = [case for case in manifest["cases"] if case.get("status") == "active"]
    match = next((case for case in active if case.get("id") == case_id), None)
    _require(match is not None, f"{case_id} is not an active case")
    if replaced_by:
        _require(replaced_by != case_id, "a case cannot replace itself")
        _require(any(case.get("id") == replaced_by for case in active),
                 f"replacement {replaced_by} is not active")
    match["status"] = "historical"
    match["retired"] = {
        "reason": reason,
        "owner": owner,
        "reviewed_at": today.isoformat(),
    }
    if replaced_by:
        match["superseded_by"] = replaced_by
    if not apply:
        return {"action": "retire", "case": match, "dry_run": True}
    original = manifest_path.read_text(encoding="utf-8")
    try:
        _write(manifest_path, manifest)
    except Exception:
        manifest_path.write_text(original, encoding="utf-8")
        raise
    return {"action": "retire", "case": match, "dry_run": False}
