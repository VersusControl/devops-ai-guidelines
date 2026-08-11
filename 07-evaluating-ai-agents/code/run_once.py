"""Run the agent once against the recorded incident and print its conclusion.

The model here is *scripted*: a plain function that returns a fixed sequence of
actions. No API key, no network, so the whole book runs the same on your laptop
and in CI. Swap `scripted_model` for a real LLM call later and nothing else in
the agent changes.
"""

from agent import Agent
from tools import get_metrics, get_logs, get_deploys, get_db_status

TOOLS = {
    "get_metrics": get_metrics,
    "get_logs": get_logs,
    "get_deploys": get_deploys,
    "get_db_status": get_db_status,
}

ALERT = {
    "service": "checkout-service",
    "summary": "checkout-service p95 latency > 2s",
}


def scripted_model(alert, observations):
    """Decide the next step from what we've seen so far.

    A real model would read the alert and the observations and reason about them.
    This stand-in walks a fixed path so the run is deterministic: check deploys,
    check the db pool, then blame the deploy.
    """
    if "get_deploys" not in observations:
        return {"type": "call_tool", "tool": "get_deploys"}
    if "get_db_status" not in observations:
        return {"type": "call_tool", "tool": "get_db_status"}
    return {
        "type": "conclude",
        "root_cause": "14:02 deploy cut DB_MAX_CONNECTIONS 50->5, exhausting the pool",
        "category": "deploy",
        "evidence": ["get_deploys", "get_db_status"],
    }


def main():
    agent = Agent(TOOLS, scripted_model)
    conclusion = agent.run(ALERT)

    print("Alert:     ", ALERT["summary"])
    print("Root cause:", conclusion.root_cause)
    print("Category:  ", conclusion.category)
    print("Evidence:  ", ", ".join(conclusion.evidence) or "(none)")
    print("Steps:     ", len(conclusion.trajectory))
    print()
    print("Was it right? You can't tell from this output. Nothing here is")
    print("compared against a known answer. That is the gap the next chapter closes.")


if __name__ == "__main__":
    main()
