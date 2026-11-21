"""Show the real agent's answer, then evaluate that same run with Jev."""

import argparse

from answer_key import load_answer_key
from config import load_settings
from jev_judge import JEV_ANSWER_MODEL, JudgePolicy, call_cloudflare, evaluate
from run_agent import CASES, run_agent, show_conclusion


DEMO_POLICY = JudgePolicy(
    approved_model=JEV_ANSWER_MODEL,
    min_quality=1.5,
    min_confidence=0.6,
    max_unsupported=0.2,
    min_unsupported_failure=0.8,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, default="pool")
    args = parser.parse_args()
    settings = load_settings(require_jev=True)
    case = CASES[args.case]
    agent_input, conclusion = run_agent(settings, case_path=case)
    print(f"Scenario: {agent_input.scenario_id}")
    show_conclusion(conclusion, settings.openai_model)
    answer = load_answer_key(case)
    if answer.scenario_id != agent_input.scenario_id:
        raise ValueError("answer belongs to another case")
    result = evaluate(
        conclusion,
        answer,
        lambda payload: call_cloudflare(payload, settings),
        DEMO_POLICY,
    )
    print(f"Hard gates: {result['hard']['gates']}")
    print(f"Evaluation: {result['status']}")
    if "judge" in result:
        judge = result["judge"]
        print(f"Jev model: {judge['model']} (rubric {judge['rubric']})")
        print(f"Explanation score: {judge['quality']['score']:.2f}")
        print(f"Unsupported claim: {judge['unsupported']['noul']:.2f}")
    elif "reason" in result:
        print(f"Judge reason: {result['reason']}")
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()