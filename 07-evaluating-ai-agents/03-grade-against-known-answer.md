## 2. Grade Your Agent Against a Known Answer

*Chapter 1 ended with a confident answer and no way to judge it. Here we close that
gap the smallest way possible: write down the truth, compare the agent's conclusion
to it, and get a real pass or fail for the first time.*

The agent from Chapter 1 investigated the checkout-service incident, checked the
deploy log and the connection pool, and concluded: *14:02 deploy cut
`DB_MAX_CONNECTIONS` 50 to 5, exhausting the pool.* Read on its own, that sentence
proves nothing. It would sound exactly as sure of itself if it were wrong. What was
missing wasn't a better answer — it was something to compare the answer against.

So let's build the smallest thing that fixes that.

### Get the code

Each chapter has its own folder, so you can run any chapter's code as it stood at
the end of that chapter without unpicking later changes:

```bash
cd devops-ai-guidelines/07-evaluating-ai-agents/code/chapter-02
```

`agent.py` and `tools.py` are carried over from Chapter 1 untouched — the agent
doesn't change in this chapter. Everything new is in three small files:
`answer.py`, `grade.py`, and `grade_once.py`.

### The move this whole book rests on

The introduction stated it in one line, and this is the chapter where it becomes
code:

> Record an incident whose correct answer you already know. Replay it to the agent.
> Score how close the agent got.

Chapter 1 already did the middle part without calling it that. The tools returned
fixed data for one incident, so the agent was investigating a frozen scene — a
replay. What's missing is the first and last part: writing the answer down, and
comparing against it.

We'll do both now, in the crudest possible form. Not because crude is good, but
because it's the fastest way to see the shape of the thing before we make it
sturdy.

### Write down what you already know

You already know what caused this incident, because Chapter 1 told you: the 14:02
deploy. Written down in a file instead of held in your head, that fact becomes an
answer key.

```python
"""answer.py — the answer key for the checkout-service incident.

Deliberately the smallest possible version: just the true category. Chapter 3
grows this into a full recorded scenario with required evidence, a distraction
to reject, and a step budget. For now it only has to answer one question: did
the agent land on the right category?
"""

from dataclasses import dataclass


@dataclass
class AnswerKey:
    """What we already know is true about an incident."""

    true_category: str  # the real root-cause category: deploy, capacity, dependency...


CHECKOUT_INCIDENT_ANSWER = AnswerKey(true_category="deploy")
```

One field. It looks too small to be worth a file, and for one incident it nearly
is. The value isn't in how much it captures — it's that it exists at all. You can't
compare anything to a shrug. You can compare something to `"deploy"`.

### A first score

With a known answer sitting next to the agent's conclusion, grading is one
comparison:

```python
"""grade.py — score a Conclusion against an AnswerKey.

The first, smallest grade: does the agent's category match the truth? Not enough
on its own — Chapter 6 adds evidence, the distraction, and step count — but it is
the first time "was it right?" has an answer instead of a shrug.
"""


def grade(conclusion, answer):
    category_match = conclusion.category == answer.true_category
    return {
        "category_match": category_match,
        "score": 1.0 if category_match else 0.0,
    }
```

Nothing clever, on purpose. `grade` never reads the prose, never judges how
well-written the root cause is, never weighs how confident it sounds. It checks the
one thing that is actually checkable: did the category match. That's a real question
with a real answer, which is more than "does this sound right?" ever gave us.

### Run it against two agents

Chapter 1's agent — call it the *careful* one — reads the deploy log and the
database status before committing. Let's grade it, and stand a weaker model next to
it: one that only reads the logs, spots the payment-provider blip at 14:06, and
blames that. That blip is the distraction planted back in Chapter 1: real, and
beside the point.

```python
"""grade_once.py — run agents against the same incident and grade each one."""

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


if __name__ == "__main__":
    main()
```

```bash
python grade_once.py
```

```text
--- careful agent ---
Root cause: 14:02 deploy cut DB_MAX_CONNECTIONS 50->5, exhausting the pool
Category:   deploy
Grade:      PASS (score 1.0)

--- hasty agent ---
Root cause: payment provider latency spike caused checkout to slow down
Category:   dependency
Grade:      FAIL (score 0.0)
```

Sit with that for a second, because it's the first real result in this book. Two
agents produced two equally fluent paragraphs about the same incident. One is now
marked PASS and the other FAIL, and neither verdict came from how the writing
reads. It came from comparing a fact to a fact.

### One match isn't enough

Before you trust this grader, try to fool it. Here's a third model — the *lucky*
one — that looks at nothing at all:

```python
def lucky_model(alert, observations):
    """Guesses right without checking anything. A guess, not a diagnosis."""
    return {
        "type": "conclude",
        "root_cause": "probably the last deploy, deploys are always breaking things",
        "category": "deploy",
        "evidence": [],
    }
```

Add `run_and_grade(lucky_model, "lucky agent")` to `main()` and run it again:

```text
--- lucky agent ---
Root cause: probably the last deploy, deploys are always breaking things
Category:   deploy
Grade:      PASS (score 1.0)
```

A passing grade for an agent that never opened a single tool. It landed on the right
category the way a stopped clock lands on the right time, and our grader can't tell
the difference, because it only ever looks at `category` and never at `evidence`.

That isn't a bug in `grade`. It's the honest limit of the smallest possible version,
and it's better to see it directly than to take it on faith. A category match tells
you the agent's *answer* was right. It says nothing about whether the agent *earned*
it — and an agent that got lucky on a recorded case will get unlucky the moment the
details shift. Chapter 6 closes this hole by requiring the right evidence to be
cited and the distraction to be rejected, not just the right label to appear.

### Why the answer has to be recorded, not remembered

Notice where `CHECKOUT_INCIDENT_ANSWER` lives: in a file, not in your head. That
matters more than it looks like it should.

Suppose the answer key had stayed as something you simply knew, the way you knew it
while reading Chapter 1. It works fine today, while the incident is fresh and the
deploy is still sitting at the top of the log. It falls apart exactly when you need
it: next month, after the deploy has scrolled away, after the pool is back to 50,
after you've half-forgotten which incident this was. You'd be grading a new agent
against your recollection of a scene that no longer looks anything like it did.

Writing it down fixes that, and gives you three properties worth naming:

- **Deterministic** — `CHECKOUT_INCIDENT_ANSWER` says the same thing on every
  import, so a score that moves means the agent moved, not your memory.
- **Repeatable** — run `grade_once.py` a hundred times, before and after every
  change to the model, for free.
- **Safe** — the agent only ever touches recorded tool output, so grading it can't
  page anyone or break anything.

Those are the same three properties a *recorded incident* gives you, and an answer
key is only half of one. The other half is the incident data itself — which right
now is still hard-coded inside `tools.py`. That works for one incident and won't
survive the dozens you'll want later.

### What's still missing

Three gaps, each pointing at a later chapter:

- **The answer key holds only a category.** No required evidence, no distraction to
  reject, no step budget. *(Chapter 3.)*
- **The grade is one boolean.** It can't express "right cause, wrong evidence" or
  "right answer, took far too long." *(Chapter 6.)*
- **The incident and its answer live in two hand-written files.** Fine for one
  incident, unworkable for fifty. *(Chapters 3–5, where both fold into one portable
  scenario.)*

None of that makes this chapter's grader wrong. It makes it the first rung rather
than the top of the ladder — and it already did the thing that matters most: it
turned "was it right?" from an opinion into a number.

### Summary

- An answer key is the fact you already know, written down instead of remembered —
  as small as one field, `true_category`, to start.
- Grading is a comparison between the agent's `Conclusion` and that key: no reading
  of tone, no judging of prose, just facts checked against facts.
- Graded on the same incident, a careful agent passed and a hasty one that fell for
  the planted distraction failed — a distinction the output alone never gave us.
- A category match is gameable: an agent that checks nothing and guesses right
  passes too. Grading evidence and trajectory, not just the label, is what closes
  that, in Chapter 6.
- The answer must be recorded rather than remembered, for the same reason a test
  fixture is: so a score change next month still means the agent changed.

Next we stop hand-writing an incident's data in one file and its answer in another,
and freeze both into a single recorded scenario the rest of the book replays.
