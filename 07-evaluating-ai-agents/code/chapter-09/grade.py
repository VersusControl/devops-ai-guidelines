"""The four deterministic Chapter 7 checks read runner-recorded actions."""

from datetime import time


def grade(conclusion, answer):
    calls = [step["tool"] for step in conclusion.trajectory if step["type"] == "call_tool"]
    consulted = set(calls) & set(conclusion.observations)
    deploys = conclusion.observations.get("get_deploys", {}).get("deploys", [])
    metrics = conclusion.observations.get("get_metrics", {})
    logs = conclusion.observations.get("get_logs", {}).get("lines", [])
    pool = conclusion.observations.get("get_db_status", {})
    try:
        alert_time = time.fromisoformat(conclusion.alert["started_at"])
        if answer.cause_effect == "pool_exhausted":
            supported_change = any(
                deploy.get("change") == answer.cause_change
                and time.fromisoformat(deploy["at"]) <= alert_time
                for deploy in deploys
            )
        else:
            supported_change = (
                metrics.get("note") == answer.cause_change
                and time.fromisoformat(metrics["change_at"]) <= alert_time
            )
    except (KeyError, ValueError, TypeError):
        alert_time = None
        supported_change = False
    if answer.cause_effect == "pool_exhausted":
        supported_effect = (
            pool.get("pool_size", 0) > 0
            and pool.get("in_use") == pool.get("pool_size")
            and pool.get("waiting", 0) > 0
        )
    elif answer.cause_effect == "dependency_slow":
        latency = metrics.get("dependency_latency_ms", [])
        supported_effect = (
            len(latency) >= 2
            and latency[-1] > latency[0]
            and any("payment-provider timeout" in line for line in logs)
        )
    elif answer.cause_effect == "capacity_limit":
        utilization = metrics.get("worker_utilization_pct", [])
        supported_effect = (
            bool(utilization)
            and utilization[-1] >= 95
            and any("worker queue backlog" in line for line in logs)
        )
    else:
        supported_effect = False
    cause = (
        conclusion.category == answer.true_category
        and conclusion.cause_change == answer.cause_change
        and conclusion.cause_effect == answer.cause_effect
        and supported_change
        and supported_effect
    )
    required = set(answer.required_evidence)
    evidence = required <= consulted and required <= set(conclusion.evidence) <= consulted
    try:
        distraction_seen = alert_time is not None and answer.distraction_source in consulted and any(
            answer.distraction_marker in line and time.fromisoformat(line[:8]) > alert_time
            for line in conclusion.observations[answer.distraction_source].get("lines", [])
        )
    except (KeyError, ValueError, TypeError):
        distraction_seen = False
    distraction_handled = (
        distraction_seen
        and any(
            isinstance(signal, str)
            and (signal == answer.distraction_id or signal.startswith(answer.distraction_id + "_"))
            for signal in conclusion.rejected_signals
        )
        and answer.distraction_id not in conclusion.cause_change
        and answer.distraction_id not in conclusion.cause_effect
    )
    gates = {
        "cause": cause,
        "evidence": evidence,
        "distraction": distraction_handled,
        "steps": len(conclusion.trajectory) <= answer.max_steps
        and bool(conclusion.trajectory)
        and conclusion.trajectory[-1]["type"] == "conclude",
    }
    return {"gates": gates, "passed": all(gates.values()), "distraction_seen": distraction_seen}