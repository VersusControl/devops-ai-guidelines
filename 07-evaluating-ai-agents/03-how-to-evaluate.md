## 2. How Do You Evaluate an Agent?

*Before writing any harness code, we need to answer a plainer question: what does it
even mean to grade an agent? This chapter is the concepts — what can be measured, what
you should choose to measure, and the smallest grader that actually works.*

### What this chapter covers

No harness yet. Three things instead:

1. Why an agent is harder to grade than ordinary software.
2. The two things you can actually grade — and why most teams only grade one.
3. How to decide *what* you're measuring, before you measure anything.

At the end we'll write a working grader in about ten lines, watch it separate a good
agent from a bad one, and then watch a third agent cheat it. That cheat is what the
rest of the book exists to fix.

### Why an agent is hard to grade

You already know how to test software. Call a function, assert on what comes back:

```python
assert add(2, 2) == 4
```

That works because two things are true: the answer is a value you can compare, and the
function has no interesting middle. It computed, it returned, done.

Neither holds for an agent. Chapter 1's agent read some tools, thought about what it
found, decided what to look at next, and eventually committed to a paragraph. That
breaks testing in two separate places.

**The answer is a judgment, not a value.** "The 14:02 deploy shrank the connection
pool" isn't `== 42`. It's prose, and prose can be right, half-right, right for the
wrong reason, or confidently wrong. There's no `==` that tells those apart.

**There's a middle, and it matters.** The agent took a path: which tools it called, in
what order, when it decided it had enough. Two agents can produce the same paragraph
having done completely different work — and one of them got lucky. A test that only
looks at the return value can't see the difference.

So grading an agent means grading something that acts, reasons across several steps,
and answers in words. That's the problem. It's harder than a unit test, and it's not
as hard as it sounds once you stop trying to grade the prose.

### The two things you can grade

Every useful check on an agent falls into one of two buckets.

**The outcome** — did it arrive at the right answer? For our agent: was the root cause
correct? This is what everyone measures first, because it's what you care about.

**The process** — did it get there in a way that will hold up next time? Which tools
did it consult? Did it look at the evidence that actually proves the cause? Did it
follow a red herring? How many steps did it burn?

Most teams grade only the outcome, and it's an understandable mistake — the outcome is
the point, after all. But grading outcomes alone is how you end up shipping an agent
that scores well and fails in production. An agent that names the right cause without
ever opening the deploy log didn't diagnose anything. It pattern-matched, or it
guessed, and it happened to be right on the case you tested. Change one detail and it
falls over.

This is why the word *trajectory* keeps coming up in agent evaluation. Grading the
path isn't academic rigor; it's the difference between measuring skill and measuring
luck.

### Decide what you're measuring first

"Is the agent good?" isn't answerable. It's four or five different questions wearing a
trench coat, and you have to pick which ones you're in the business of answering.

There are at least five things you could mean by "good":

| Dimension | The question | This book |
|---|---|---|
| Quality | Does it get the right answer, for the right reasons? | yes — this is the whole focus |
| Cost | How many tokens, tool calls, dollars per run? | partly — via the step budget |
| Latency | How long does a run take? | no |
| Safety | Can it do damage? Does it refuse what it should? | no — our agent is read-only by design |
| Consistency | Same input, same answer, run to run? | touched on in Chapter 9 |

Pick deliberately, and write it down. A harness that quietly tries to measure
everything measures nothing well, and you'll never be able to explain what a score
means. Ours answers one question: **given a case whose answer we know, does the agent
get it right for the right reasons, without wasting effort?**

The second scoping decision matters just as much: **one task per harness.** Our agent
does root-cause diagnosis from an alert. If it also wrote postmortems and answered
questions in Slack, those would each need their own scenarios and their own checks,
because "good" means something different for each. Evaluate one job at a time.

If you're building this for your own agent, stop here and write two sentences: the
dimension you're grading, and the single task you're grading it on. Everything
downstream inherits those two choices.

### The smallest grader that works

Concepts are cheap, so let's make one real. The scoping decision above says we're
grading quality on one task, so the simplest possible version of that is: write down
the correct answer, and compare.

```bash
cd devops-ai-guidelines/07-evaluating-ai-agents/code/chapter-02
```

The known answer, in a file rather than in your head:

```python
@dataclass
class AnswerKey:
    """What we already know is true about a case."""
    true_category: str


CHECKOUT_INCIDENT_ANSWER = AnswerKey(true_category="deploy")
```

And the grade — one comparison:

```python
def grade(conclusion, answer):
    category_match = conclusion.category == answer.true_category
    return {
        "category_match": category_match,
        "score": 1.0 if category_match else 0.0,
    }
```

Nothing here reads the prose, weighs the tone, or judges how confident the agent
sounded. It checks the one thing that's checkable. Run it against Chapter 1's careful
agent and against a hasty one that only reads the logs and blames the payment provider
blip at 14:06:

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

That's the first real result in this book. Two equally fluent paragraphs, and now one
of them is marked wrong — not because of how it reads, but because a fact didn't match
a fact.

### The agent that cheats it

Now try to break it. Here's a third agent that examines nothing at all:

```python
def lucky_model(alert, observations):
    """Guesses without checking anything. A guess, not a diagnosis."""
    return {
        "type": "conclude",
        "root_cause": "probably the last deploy, deploys are always breaking things",
        "category": "deploy",
        "evidence": [],
    }
```

```text
--- lucky agent ---
Category:   deploy
Grade:      PASS (score 1.0)
```

A passing grade for an agent that never opened a tool. It landed on the right category
the way a stopped clock lands on the right time.

That's not a bug in `grade` — it's the honest limit of grading outcomes only, which is
exactly the failure this chapter warned about two sections ago, now visible in
output. And it's the reason the rest of the book isn't just "write more answer keys."

### What a complete grade needs

Fixing the lucky agent means checking the process, not only the outcome. Four checks
cover it, and every one of them is a thing a human reviewer would ask:

- **Right cause** — did the answer match the truth? *(outcome)*
- **Right evidence** — did it consult the signals that actually prove the cause?
  *(process)*
- **Rejected the distraction** — did it ignore the planted red herring? *(process)*
- **Step count** — did it get there without thrashing? *(process)*

One outcome check and three process checks. That ratio is the point of this chapter.
Chapter 7 turns all four into code; everything between here and there exists to make
them possible.

### Where else this applies

Nothing above is specific to incidents. Any tool-using agent has an outcome and a
path, and the same four checks translate directly:

| Agent | Right answer | Right evidence | Distraction | Effort |
|---|---|---|---|---|
| Incident diagnosis | the true root cause | the deploy log, the pool status | a coincidental latency blip | tool calls |
| Customer support | the correct resolution | the policy that justifies it | an angry but irrelevant complaint | replies to resolve |
| SQL / analytics | the correct result | the tables that must be joined | a deprecated lookalike table | queries run |
| Code fixing | the working fix | the test that must pass | an unrelated failing test | files touched |
| Research | the correct answer | the sources that support it | a plausible but wrong source | searches |

If you're evaluating something else, you don't need a different method. You need to
fill in that row for your agent.

### Summary

- Agents resist ordinary testing for two reasons: the answer is a judgment rather than
  a value, and the middle — the path — matters.
- There are exactly two things to grade: the **outcome** and the **process**. Grading
  outcomes alone is how a lucky agent passes.
- Scope before you measure. Pick which dimension of "good" you mean (we chose quality),
  and grade one task at a time.
- The smallest useful grader is a known answer plus a comparison. It's enough to
  separate a careful agent from a hasty one — and not enough to catch a guess.
- A complete grade is four checks: right cause, right evidence, rejected the
  distraction, sensible effort. One outcome, three process.

Next: the map. Before we build any of this, one page showing all five parts of the
harness and which chapter builds each.
