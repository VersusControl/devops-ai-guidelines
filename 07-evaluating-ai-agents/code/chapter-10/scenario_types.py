"""Agent input and grader-only answer are different records."""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class AgentInput:
    scenario_id: str
    alert: Dict[str, str]
    tool_responses: Dict[str, Any]


@dataclass(frozen=True)
class AnswerKey:
    scenario_id: str
    true_category: str
    true_cause: str
    cause_change: str
    cause_effect: str
    required_evidence: List[str]
    distraction: str
    distraction_source: str
    distraction_marker: str
    distraction_id: str
    max_steps: int