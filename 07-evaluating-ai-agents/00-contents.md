<!-- Cover -->

<h1 align="center" style="border-bottom: none">
  <img alt="The Versus SRE Agent" src="https://cdn.jsdelivr.net/gh/VersusControl/devops-ai-guidelines@main/07-evaluating-ai-agents/images/evaluating-ai-agents.svg" width="300">
</h1>

<div align="center">

**GUIDE**

# Evaluating AI Agents

### How to Measure and Improve Any Tool-Using Agent — Using a DevOps Incident Agent as the Running Example

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
book is about: a confident answer, and no way to tell if it was right.

**2. [How Do You Evaluate an Agent?](#2-how-do-you-evaluate-an-agent)**
Why an agent is harder to grade than a function, the two things you can actually
grade (the answer and the path to it), and how to scope what you'll measure before
you measure anything. Ends with the smallest grader that works — and the agent that
cheats it.

**3. [The Harness We're Going to Build](#3-the-harness-were-going-to-build)**
The map of the whole book on one page: five parts, how they fit together, and which
chapter builds each. Read this and every chapter after it has an obvious place to sit.

**4. [Record a Test Case Your Agent Will Face](#4-record-a-test-case-your-agent-will-face)**
Freeze one case into a scenario file: the situation the agent is dropped into, and a
separate answer key holding the true cause, the evidence that proves it, the planted
distraction, and the step budget.

**5. [Replay That Case to Your Agent](#5-replay-that-case-to-your-agent)**
Swap the agent's live data sources for recorded ones of the exact same shape. The
agent investigates a frozen scene and can't tell the difference — which is what makes
a score mean something.

**6. [Keep the Answer Away from the Agent](#6-keep-the-answer-away-from-the-agent)**
Enforce the wall between the two parts of a scenario instead of trusting yourself to
respect it. Why this anti-cheat is the most important rule in the design.

**7. [Score It with Hard Gates](#7-score-it-with-hard-gates)**
The deterministic checks and why each exists: right category, cited the evidence that
proves it, rejected the distraction, stayed inside the step budget. No opinions, no
arguing.

**8. [Add an LLM Judge for the Judgment Calls](#8-add-an-llm-judge-for-the-judgment-calls)**
Grade what rules can't express, using a language model and a plain-language rubric —
kept firmly as a second opinion that never decides pass or fail.

**9. [Turn Scores into a Benchmark](#9-turn-scores-into-a-benchmark)**
Run many scenarios and roll the results into one number you track over time, so you
can prove an improvement and catch a regression.

**10. [Close the Loop: Every Miss Becomes a Test](#10-close-the-loop-every-miss-becomes-a-test)**
Turn a real production failure into a new recorded scenario. The benchmark grows
along your agent's actual weaknesses instead of your guesses.

**11. [Gate Your Agent in CI](#11-gate-your-agent-in-ci)**
Run the benchmark as a merge gate, point the whole harness at your own agent, and
operate it honestly. What it catches, and what it never will.

**[Additional Resources](#additional-resources)**
