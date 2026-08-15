"""grade_once.py — run agents against the same incident and grade each one.

The lucky agent passing is the point, not an oversight: a category-only grade
can't tell a real diagnosis from a guess. Chapter 6 fixes that.
"""

from agent import Agent
from tools import get_metrics, get_logs, get_deploys, get_db_status
from answer import CHECKOUT_INCIDENT_ANSWER
from grade import grade

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


def careful_model(alert, observations):
    """Checks the deploy log and the db pool, blames the deploy. Chapter 1's agent."""
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


def hasty_model(alert, observations):
    """Reads only the logs and trips on the payment-provider blip at 14:06."""
    if "get_logs" not in observations:
        return {"type": "call_tool", "tool": "get_logs"}
    return {
        "type": "conclude",
        "root_cause": "payment provider latency spike caused checkout to slow down",
        "category": "dependency",
        "evidence": ["get_logs"],
    }


def lucky_model(alert, observations):
    """Guesses right without checking anything. A guess, not a diagnosis."""
    return {
        "type": "conclude",
        "root_cause": "probably the last deploy, deploys are always breaking things",
        "category": "deploy",
        "evidence": [],
    }


def run_and_grade(model, label):
    conclusion = Agent(TOOLS, model).run(ALERT)
    result = grade(conclusion, CHECKOUT_INCIDENT_ANSWER)

    print(f"--- {label} ---")
    print("Root cause:", conclusion.root_cause)
    print("Category:  ", conclusion.category)
    print("Grade:     ", "PASS" if result["category_match"] else "FAIL",
          f"(score {result['score']})")
    print()


def main():
    run_and_grade(careful_model, "careful agent")
    run_and_grade(hasty_model, "hasty agent")
    run_and_grade(lucky_model, "lucky agent")


if __name__ == "__main__":
    main()
