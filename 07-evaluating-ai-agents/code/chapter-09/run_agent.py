"""Run the OpenAI agent once against the checkout recording, without judging."""

import argparse
from copy import deepcopy
from pathlib import Path

from openai import OpenAI

from agent import INSTRUCTIONS, Agent
from agent_input import load_agent_input
from config import load_settings
from replay import build_replay_tools
from validity import check_case


CASE = Path(__file__).parent / "scenarios/checkout-latency.json"
CASES = {
    "pool": CASE,
    "dependency": CASE.parent / "payment-dependency.json",
    "capacity": CASE.parent / "worker-capacity.json",
}
CURRENT_SYSTEM = {
    "topology": "checkout-db-pool-v1",
    "runbook": "checkout-latency-v2",
    "tool_contract": "incident-tools-v1",
}


def run_agent(settings, client=None, alert_message=None, case_path=CASE,
              instructions=INSTRUCTIONS, max_steps=5):
    check_case(case_path, CURRENT_SYSTEM)
    agent_input = load_agent_input(case_path)
    alert = deepcopy(agent_input.alert)
    if alert_message is not None:
        if not isinstance(alert_message, str) or not alert_message.strip():
            raise ValueError("alert message must be nonempty text")
        alert["message"] = alert_message
    client = client if client is not None else OpenAI(api_key=settings.openai_api_key)
    conclusion = Agent(
        client=client,
        tools=build_replay_tools(agent_input),
        model=settings.openai_model,
        max_steps=max_steps,
        instructions=instructions,
    ).run(alert)
    return agent_input, conclusion


def show_conclusion(conclusion, model):
    print(f"Agent model: {model}")
    print(f"Alert: {conclusion.alert['message']}")
    print("Tool calls: " + ", ".join(
        step["tool"] for step in conclusion.trajectory if step["type"] == "call_tool"
    ))
    print(f"Root cause: {conclusion.root_cause}")
    print(f"Category: {conclusion.category}")
    print(f"Cause change: {conclusion.cause_change}")
    print(f"Cause effect: {conclusion.cause_effect}")
    print("Cited evidence: " + ", ".join(conclusion.evidence))
    print("Rejected signals: " + ", ".join(conclusion.rejected_signals))
    print(f"Steps: {len(conclusion.trajectory)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, default="pool")
    args = parser.parse_args()
    settings = load_settings()
    agent_input, conclusion = run_agent(settings, case_path=CASES[args.case])
    print(f"Scenario: {agent_input.scenario_id}")
    show_conclusion(conclusion, settings.openai_model)


if __name__ == "__main__":
    main()