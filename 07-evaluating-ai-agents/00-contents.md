<!-- Cover -->

<h1 align="center" style="border-bottom: none">
  <img alt="The Versus SRE Agent" src="https://cdn.jsdelivr.net/gh/VersusControl/devops-ai-guidelines@main/07-evaluating-ai-agents/images/evaluating-ai-agents.svg" width="300">
</h1>

<div align="center">

**GUIDE**

# Evaluating AI Agents

### How to Measure and Improve Any Tool-Using Agent

*Everyone can build an agent now; almost no one can prove theirs is getting better. This book teaches the missing skill — scoring an agent against recorded cases whose answers you already know — built end to end on a DevOps and SRE incident agent, and ready to point at your own.*

</div>

---

<!-- Table of Contents -->

## Contents

**0. [Introduction](#introduction)** — Why every team can build an agent but few can
grade one, the one idea that fixes it, and why we learn the skill on a DevOps incident
agent you'll measure from cover to cover.

**1. [Build the AI Agent This Book Runs On](#1-build-the-ai-agent-this-book-runs-on)**
Build the tiny incident-diagnosis agent, run it once, and hit the wall the whole
book is about: it gives you a confident answer and no way to tell if it was right.

**2. [Grade Your Agent Against a Known Answer](#2-grade-your-agent-against-a-known-answer)**
The core idea. Record an incident whose correct answer you already know, replay it
to the agent, and score how close it got. Why a recorded case is the only thing
that gives you a number you can trust.

**3. [Record an Incident Your Agent Will Face](#3-record-an-incident-your-agent-will-face)**
Freeze one incident into a scenario: the situation the agent is dropped into, plus
a hidden answer key — the true root cause and its category, the evidence that
proves it, the planted distraction to reject, and a step budget.

**4. [Replay a Recorded Incident to Your Agent](#4-replay-a-recorded-incident-to-your-agent)**
Swap the agent's live data sources for recorded ones that return the exact same
shape. The agent investigates normally against a fixed scene and can't tell the
difference.

**5. [Hide the Answer, Then Run the Agent](#5-hide-the-answer-then-run-the-agent)**
Strip the answer key before the agent ever sees it. Why this anti-cheat is the
most important rule of the whole design.

**6. [Score the Agent on the Hard Gates](#6-score-the-agent-on-the-hard-gates)**
The deterministic gates and why each one matters: right root-cause category, cited
the required evidence (not just the right answer), rejected the planted distraction,
stayed within the step budget. Every gate must pass.

**7. [Add an LLM Judge for Your Agent](#7-add-an-llm-judge-for-your-agent)**
Add a language-model grader against a plain-language rubric to catch the nuance the
rules can't express — and keep it as a second opinion that never decides pass or
fail.

**8. [Turn Your Agent's Scores Into a Benchmark](#8-turn-your-agents-scores-into-a-benchmark)**
Run many scenarios and roll pass/fail into one number you track over time — to
catch regressions and prove real improvement.

**9. [Close the Loop: Every Agent Miss Becomes a Test](#9-close-the-loop-every-agent-miss-becomes-a-test)**
Turn a real production miss into a new recorded scenario with its own answer key.
The benchmark grows along your agent's real weaknesses.

**10. [Gate Your Agent in CI](#10-gate-your-agent-in-ci)**
Run the benchmark as a merge gate, apply it to your own real agent, and operate it
honestly. What it catches, what it doesn't.

**[Additional Resources](#additional-resources)**
