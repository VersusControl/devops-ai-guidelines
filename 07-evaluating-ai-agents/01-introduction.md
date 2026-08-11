## Introduction

*Today almost every team is building its own AI agent. The hard part isn't building one — it's knowing whether it's any good, and how to make each change move it forward. That skill is evaluation, and this book teaches it using DevOps and SRE as the running example.*

### Everyone is building an agent. Almost no one can grade one.

Right now, on teams of every size, someone is wiring a language model into a loop of
tools and calling it an agent. A framework here, a clever prompt there, a handful of
functions it can call — and in an afternoon you have something that reads a problem,
takes a few actions, and comes back with an answer. Building one has never been
easier.

The part nobody has figured out is the one that comes right after: **is it any good,
and is my next change making it better or worse?** You tweak the prompt, swap the
model, add a tool — and then you stare at a couple of outputs and guess. There's no
test suite that turns green, no number that goes up. So the agent changes on gut
feel: it might be improving, it might be quietly getting worse, and you can't prove
either.

That question — *how do I measure this agent so I can actually improve it?* — is the
skill this book teaches. Not how to build an agent (you can already do that), but how
to **evaluate one**: put a number on its quality, watch that number move when you
change something, and stop shipping changes on hope.

### Why this book lives in DevOps and SRE

Evaluation is a general skill, but it only makes sense when it's concrete — so this
book works in one context from the first page to the last: **DevOps and SRE**, the
on-call world of alerts, logs, deploys, and root-cause investigation.

Two roles run that world, and it helps to name them. A **DevOps engineer** builds and
operates the pipeline that ships and runs software — the deploys, the config, the
infrastructure. An **SRE** (site reliability engineer) keeps the running system
healthy: when something breaks, the SRE reads the logs, metrics, and recent changes,
works out the root cause, and mitigates. Most of an incident is that second job — the
investigation.

That investigation is exactly the work teams are now handing to AI agents, which
makes it the perfect thing to learn evaluation on. The agent we'll grade does what an
on-call engineer does: an alert fires, it gathers signals (metrics, logs, recent
deploys), forms a hypothesis, checks it against more signals, and emits a root-cause
report — the cause, the evidence, and a next step. Everything you learn here transfers
to any tool-using agent, but nothing in these pages stays abstract: every example is a
real incident with a real right answer.

And almost none of the teams building this agent today can tell you how good it is.

### The problem

Here is a Tuesday afternoon you have probably lived.

An alert fires: `checkout-service p95 latency > 2s`. Your agent picks it up — it
reads the metrics, tails the logs, checks recent deploys, and comes back with a
paragraph: *"Root cause: the 14:02 deploy cut the database connection pool from 50
to 5, so requests queued waiting for a connection and checkout timed out."* It
sounds right. You act on it. The incident resolves.

A week later you change the agent. You switch the model, reword the prompt, add a
tool, or bump the step budget so it stops giving up early. You run it against a
fresh alert. It answers again — confident, plausible, well-written.

And now the question that has no answer: **did your change help?**

You can't tell. The new incident is different from the old one, so the two runs
aren't comparable. The agent sounds just as sure whether it's right or wrong —
fluent prose is not evidence. And you can't re-run last week's incident, because
production has moved on: the deploy is old, the pool is back to normal, the logs
have rotated. The one moment you could have graded is gone.

So you do what everyone does. You look at a couple of outputs, decide it "seems
better," and ship. You are tuning by guesswork. You can't put a number on the
agent, you can't defend it to anyone who asks "how good is it," and you certainly
can't put it in CI and block a merge that quietly made it worse.

That gap — between *the agent produced an answer* and *we know how good the agent
is* — is what this book closes.

### Why the usual tools don't cover it

We already know how to measure ordinary software. Give a function an input, assert
on its output, the test passes or fails. Machine-learning teams have their version
too: hold out some labeled examples, run the model, compare predictions to the
labels, report accuracy. Neither is new.

An incident-response agent breaks both. It doesn't compute one output from one
input — it *investigates*. It decides which tool to call, reads what comes back,
decides what to look at next, and stops when it thinks it has the answer. Two things
make that hard to grade:

- **The answer is a judgment, not a value.** "The 14:02 deploy shrank the connection
  pool" isn't `== 42`. It's prose that can be right, half-right, or confidently
  wrong, and you need a way to score *how close* it got.
- **How it got there matters as much as the answer.** An agent that names the right
  cause but never looked at the deploy log got lucky, and luck doesn't survive the
  next incident. You have to grade the *trajectory* — the path of tool calls — not
  just the final paragraph.

You need to measure something that acts, reasons over several steps, and answers in
words. That's the problem. The good news is we've solved its twin before.

### The coding world already solved this

A few years ago, AI coding assistants were in the same spot: obviously useful,
impossible to compare. Then the field agreed on a shared benchmark — **SWE-bench**,
a big set of real coding tasks each shipped with a *known answer key*. Suddenly
"is this coding agent better?" had a number behind it. You could run any agent
against the same fixed tasks, score it, and watch the score climb release over
release. A lot of the rapid progress that followed traces back to simply having
that shared measure.

Incident response never had its SWE-bench. So progress stayed a matter of opinion,
and every team re-learned the same "it seems better" habit in private. The fix is
to build the missing benchmark — a set of recorded incidents, each with a known
answer, that you can replay to any agent and score. That's the whole idea behind
this book, applied to the DevOps and SRE work above and small enough to build by
hand.

### The one idea

Everything here rests on a single move:

> **Record an incident whose correct answer you already know. Replay it to the
> agent. Score how close the agent got.**

If you know the truth ahead of time — *this* was the root cause, *this* is the
evidence that proves it, *this* was the misleading signal to ignore — then when the
agent runs, you can grade it. Right cause or wrong? Did it cite the evidence, or
just guess? Did it get fooled by the distraction? Did it answer in a few steps or
keep going in circles?

The word doing the work is **recorded**. Instead of pointing the agent at live
production — which changes every second and never gives you the same incident
twice — you capture one incident once, with its answer, and hand the agent a frozen
copy of the scene. A recorded case is worth building on because it is:

- **Deterministic** — the same inputs every run, so a score change means the *agent*
  changed, not the world.
- **Repeatable** — run it a thousand times, before and after every code change, for
  free.
- **Cheap** — no real outage, no waiting for prod to break in an interesting way.
- **Safe** — the agent investigates a recording, so it can't touch anything real
  while you're grading it.

This is the same idea behind a held-out test set in machine learning, or a
golden-file test in ordinary code: freeze a known-good case, replay it, compare.
What's new is applying it to something that *acts* — and grading not just the answer
but the path it took to get there.

### What a good score measures

"Score how close the agent got" is only useful if we're precise about *what* we're
grading. A recorded incident lets us check four things a real SRE reviewer would
check:

- **Right cause** — did it land on the true cause, or something close but wrong?
- **Right evidence** — did it look at the signals that actually prove the cause, or
  reach the answer without earning it?
- **Ignored the distraction** — did it reject the planted false signal, or follow
  it?
- **Step count** — did it get there in a reasonable number of steps, or keep going
  until it ran out of budget?

Those four turn a vague "seems better" into things you can pass or fail. We'll make
each one concrete in Chapter 6.

### The DevOps incident we'll use the whole way through

Abstract talk about "scenarios" gets vague fast, so this book carries one
concrete incident from the first chapter to the last. You already met it above:

> **Alert:** `checkout-service p95 latency > 2s`.
>
> **What really happened:** a 14:02 deploy changed `DB_MAX_CONNECTIONS` from 50 to
> 5. The connection pool ran dry, requests piled up waiting for a free connection,
> and checkout requests timed out.
>
> **The proof:** the deploy log shows the config change at 14:02; the database
> status shows all 5 connections in use with 40 requests waiting.
>
> **The trap:** at 14:06 the payment provider's latency ticked up from 90ms to
> 180ms — real, visible in the logs, and completely beside the point. A good agent
> notices it and rules it out. A weak one blames it and stops.

That single incident is enough to exercise every part of the harness: a true cause
with a category (`deploy`), the specific evidence that proves it, a planted
distraction to reject, and a natural limit on how many steps a good investigation
should take. When we score the agent, we're scoring it against exactly this.

### What you'll build

By the end you'll have a small, working evaluation harness — a few hundred lines of
Python, no framework — that does the whole loop:

- A **tiny incident-diagnosis agent** with four read-only tools, so you have a real
  agent to measure (Chapter 1).
- A **recorded scenario** format: the incident the agent sees, plus a hidden answer
  key it doesn't (Chapters 3–5).
- A **replay** mechanism that feeds the agent recorded data of the same shape its
  live tools return (Chapter 4).
- **Deterministic gates** — right category, required evidence cited, distraction
  rejected, step budget respected — that pass or fail with no argument (Chapter 6).
- An **LLM judge** for the nuance the gates can't express, kept firmly as a second
  opinion (Chapter 7).
- A **benchmark**: many scenarios rolled into one score you track over time
  (Chapter 8).
- A **closed loop** that turns every production miss into a new recorded case, and a
  **CI gate** that blocks any change which drops the score (Chapters 9–10).

Start to finish, it answers the Tuesday question: *my agent scored 8 out of 10 last
week; my change took it to 9; here's the case it now gets right that it used to
miss.*

### Who this is for

You're comfortable reading Python and you've either built an agent that calls tools
or you're about to. You don't need a machine-learning background — there's no
training and no math beyond counting how many cases passed. If you've ever shipped a
change to an AI system and thought *I hope that helped*, this book is about replacing
the hope with a number.

Everything is built from scratch so you can see every moving part. No evaluation
framework, no vendor. Once you've built one by hand, the commercial ones stop being
magic — you'll know exactly what they're doing, because you'll have done it
yourself.

Let's start by building the agent we're going to measure.
