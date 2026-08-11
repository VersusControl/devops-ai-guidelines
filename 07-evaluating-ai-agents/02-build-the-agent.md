## 1. Build the AI Agent This Book Runs On

*Before you can measure an agent, you need an agent. We'll build a small one that
diagnoses a real incident — and then discover we have no idea if it's any good.*

You can't measure something that doesn't exist yet. So this chapter builds the
agent the whole book is about: a small incident-diagnosis agent that takes an
alert, investigates by calling read-only tools, and commits to a root cause. It's
a few dozen lines. That's on purpose — every part of it stays visible, and every
part of it is something the harness in later chapters will grade.

At the end we'll run it once, watch it produce a confident answer, and hit the wall
that the rest of the book is built to climb: **the agent tells us what it thinks,
and gives us no way to know if it's right.**

### Get the code

Everything in this book is in one repository. Clone it and work from the code
folder for this book:

```bash
git clone https://github.com/VersusControl/devops-ai-guidelines.git
cd devops-ai-guidelines/07-evaluating-ai-agents/code
```

You'll need Python 3.9 or newer. There are no third-party packages — everything is
standard library, so there's nothing to install. Browse the code here:
[github.com/VersusControl/devops-ai-guidelines/tree/main/07-evaluating-ai-agents/code](https://github.com/VersusControl/devops-ai-guidelines/tree/main/07-evaluating-ai-agents/code).

### What the agent does

Give it an alert like `checkout-service p95 latency > 2s`, and it should do what a
tired on-call engineer does at 2am: look at the obvious things — recent deploys,
the logs, the database — form a theory, and stop once the theory holds together.

An agent is just a loop around a decision. Each turn it decides *what to do next*:
call another tool to learn more, or stop and commit to an answer. What makes it an
*agent* rather than a script is that the decision isn't hard-coded — it's made by a
model looking at what's been seen so far.

We'll build it in three pieces:

- **Tools** — the read-only things the agent can look at.
- **The agent** — the loop that calls tools and commits to a conclusion.
- **A run** — wiring it to a model and running it once.

### The tools

Our agent gets four read-only tools. Each returns recorded data for one incident:
the checkout-service latency spike from the introduction. Read-only matters — an
agent you're grading should look but never touch, so a bad run can't break
anything.

```python
def get_metrics(service):
    """Recent latency and error-rate metrics for a service."""
    return {
        "service": service,
        "window": "14:00-14:10",
        "p95_latency_ms": [420, 430, 450, 1900, 2100, 2200, 2150],
        "error_rate": [0.01, 0.01, 0.02, 0.08, 0.11, 0.12, 0.12],
        "note": "p95 crosses 2s at 14:03, one minute after the 14:02 deploy",
    }


def get_logs(service):
    """A sample of recent log lines for a service."""
    return {
        "service": service,
        "lines": [
            "14:03:01 WARN  db pool: waiting for connection (waiters=12)",
            "14:03:04 WARN  db pool: waiting for connection (waiters=27)",
            "14:03:09 ERROR checkout: timeout acquiring db connection after 2000ms",
            # A coincidence, not the cause. A good diagnosis ignores this line.
            "14:06:12 INFO  payment-provider latency 180ms (was 90ms)",
        ],
    }
```

The other two, `get_deploys` and `get_db_status`, return the deploy history and the
connection-pool status. Together the four tools tell the whole story: a 14:02 deploy
cut `DB_MAX_CONNECTIONS` from 50 to 5, the pool ran dry, and checkout timed out. The
proof is in `get_deploys` (the config change) and `get_db_status` (5 of 5
connections in use, 40 waiting).

Notice the last log line. The payment provider got slower at 14:06 — real, and
completely beside the point. It's the distraction from the introduction, planted
right where a hasty agent will trip on it. We'll use it to tell a careful agent from
a lucky one.

One more thing to notice, because it's the key idea of the whole book: right now these
functions return hard-coded data. Later they'll return the same shapes from a
recording instead, and the agent won't be able to tell the difference. That
swap — live tools for recorded ones — is what makes an incident replayable.

### The agent

The agent commits to a `Conclusion`: what it decided, and how it got there.

```python
@dataclass
class Conclusion:
    """What the agent decided, and how it got there."""

    root_cause: str                                 # the cause, in the agent's words
    category: str                                   # a coarse bucket: deploy, capacity, dependency
    evidence: list = field(default_factory=list)    # tool names it relied on
    trajectory: list = field(default_factory=list)  # the steps it took, in order
```

Two of those fields are the answer (`root_cause`, `category`). The other two are how
it got there (`evidence`, `trajectory`). That split is deliberate — later we'll
grade both. An agent that names the right cause but never looked at the deploy log
got lucky, and the `trajectory` is how we catch it.

The loop itself is small:

```python
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
```

Three details worth pausing on:

- **The decision is injected.** The agent doesn't decide anything itself — it asks
  `call_model` what to do next. That lets us run the exact same agent against a
  scripted stand-in (deterministic, no API key) or a real LLM. The harness grades
  the `Conclusion`, so it never has to care which one produced it.
- **Every step is recorded** in `trajectory`. Nothing is graded that we didn't
  keep.
- **There's a step budget** (`max_steps`). A real agent that never stops is a real
  bill and a real hang. Running out of budget is itself a kind of failure, and the
  code makes it an explicit, gradeable outcome instead of an infinite loop.

### Running it once

To run the agent we need a model — the thing that decides the next step. For now
we use a *scripted* one: a plain function that walks a fixed path. No network, no
API key, so the book runs the same on your laptop and in CI. Swap it for a real LLM
call later and nothing else in the agent changes.

```python
def scripted_model(alert, observations):
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
```

Wire it up and run:

```bash
python run_once.py
```

```text
Alert:      checkout-service p95 latency > 2s
Root cause: 14:02 deploy cut DB_MAX_CONNECTIONS 50->5, exhausting the pool
Category:   deploy
Evidence:   get_deploys, get_db_status
Steps:      3

Was it right? You can't tell from this output. Nothing here is
compared against a known answer. That is the gap the next chapter closes.
```

There it is — a clean diagnosis. It checked the deploys, checked the pool, blamed
the deploy, and cited both. Three steps, no wasted moves. If you saw this output
you'd nod and move on.

### The wall

Now read that output again and answer the book's question: **is this agent any
good?**

You can't say. And it's worth being precise about *why*, because each reason maps to
a piece of the harness we're about to build:

- **Nothing was compared to a known answer.** The agent asserted a root cause. There
  was no truth on the other side of the equals sign. *(Chapters 2–3: record the
  answer.)*
- **The confident tone is worthless as evidence.** It would read exactly this
  self-assured if it had blamed the payment provider instead. *(Chapter 6: score the
  answer, not the prose.)*
- **We never checked whether it earned the answer.** It cited `get_deploys` and
  `get_db_status` this time — but nothing in the run *required* that. *(Chapter 6:
  grade the evidence and the trajectory, not just the conclusion.)*
- **We can't repeat it against tomorrow's version.** Change the model next week and
  this run is gone; there's nothing to compare against. *(Chapters 4 and 8: replay
  and benchmark.)*

That's the whole motivation for the book, sitting in one screen of output: a fluent
answer and no way to know if it's right, no way to know if it earned it, and no way
to tell if your next change made it better or worse.

The next chapter takes the first step out of the hole. We'll write down the answer
we already know — this incident's true cause, its category, and the evidence that
proves it — and score the agent's conclusion against it. The moment there's a known
answer on the other side, "was it right?" stops being a shrug and becomes a number.

### Summary

- An agent is a loop around a decision: each turn it calls a tool to learn more or
  commits to a conclusion.
- We built a small incident-diagnosis agent with four read-only tools, a step
  budget, and an injected `call_model` so it runs against a scripted stand-in or a
  real LLM without changing.
- The agent records both the answer (`root_cause`, `category`) and how it got there
  (`evidence`, `trajectory`) — because later we grade both.
- The tools return recorded data for one incident today, and will return the same
  shapes from a recording later. That swap is what makes an incident replayable.
- Run once, the agent gives a confident diagnosis and no way to judge it. Closing
  that gap is the rest of the book.
