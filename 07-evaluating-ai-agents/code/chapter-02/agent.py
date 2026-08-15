"""A tiny incident-diagnosis agent.

The agent investigates an alert by calling read-only tools in a loop, then
commits to a conclusion. The part that decides *what to do next* is injected as
`call_model`, so the same agent runs against a scripted model (no API key,
deterministic) or a real LLM. The harness we build later grades the conclusion,
so it never has to care which model produced it.

Unchanged from Chapter 1.
"""

from dataclasses import dataclass, field


@dataclass
class Conclusion:
    """What the agent decided, and how it got there."""

    root_cause: str                                 # the cause, in the agent's words
    category: str                                   # a coarse bucket: deploy, capacity, dependency
    evidence: list = field(default_factory=list)    # tool names it relied on
    trajectory: list = field(default_factory=list)  # the steps it took, in order


class Agent:
    def __init__(self, tools, call_model, max_steps=6):
        self.tools = tools
        self.call_model = call_model
        self.max_steps = max_steps

    def run(self, alert):
        observations = {}   # tool name -> what that tool returned
        trajectory = []     # every action, in order, for later grading

        for _ in range(self.max_steps):
            action = self.call_model(alert, observations)
            trajectory.append(action)

            if action["type"] == "call_tool":
                name = action["tool"]
                observations[name] = self.tools[name](alert["service"])
                continue

            if action["type"] == "conclude":
                return Conclusion(
                    root_cause=action["root_cause"],
                    category=action["category"],
                    evidence=action.get("evidence", []),
                    trajectory=trajectory,
                )

        # Ran out of steps without committing to an answer.
        return Conclusion(
            root_cause="(no conclusion: step budget exhausted)",
            category="unknown",
            evidence=[],
            trajectory=trajectory,
        )
