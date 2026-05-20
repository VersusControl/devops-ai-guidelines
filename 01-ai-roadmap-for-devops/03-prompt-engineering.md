# Prompt Engineering for DevOps

*Turning the model into a reliable component instead of a chat partner.*

> ⭐ Star this repo if you find it useful.

---

## The Problem with "Just Ask Better"

The first time I shipped an LLM-powered tool to production, I had spent two days polishing the prompt. It worked great in my terminal. The morning it went live, a teammate ran it on a different log file and got a confident, completely wrong analysis.

Prompts that work once aren't prompts. They're lucky outputs. The job of prompt engineering is to make the lucky outputs the only kind.

This chapter is about how to do that — for real DevOps tasks, with real APIs, in real production code. Not the "write better prompts" content you've seen ten times.

By the end you'll be able to:

- Write prompts that produce structured, parseable output every time
- Debug a prompt that works 80% of the time and figure out the 20%
- Build reusable templates for the tasks you do every week
- Know when prompt engineering is the wrong answer and you need tools, retrieval, or a different model

---

## What a Prompt Actually Is

A prompt is not "the thing you type." A prompt is **every token the model sees before it generates its first response token.** That includes:

- The system message (your standing instructions)
- The conversation history
- Any retrieved documents you stuffed in
- Tool definitions and their schemas
- The user's actual message
- Any few-shot examples

All of that competes for the same context window. If you have 32K tokens of history and 100 tokens of instructions, the instructions are background noise. This is the single most common reason prompts "stop working" — the prompt didn't change, the context around it did.

---

## The Five-Part Structure

Most production prompts have the same shape. Memorize it:

1. **Role** — who the model is
2. **Context** — what it needs to know
3. **Task** — what it should do
4. **Format** — what the output looks like
5. **Constraints** — what it must not do

Here's the same instruction with and without that structure.

**Lazy:**

```
Look at these logs and tell me what's wrong.
```

**Structured:**

```
You are a senior SRE triaging an incident.

Context:
- Service: payments-api (Node.js, on EKS)
- Symptom: latency p99 climbed from 200ms to 4s starting 09:14 UTC
- Last deploy: 08:45 UTC, image tag payments-api:v2.41.3

Task: Read the log excerpt and identify the most likely root cause.

Output format (strict JSON, no prose):
{
  "root_cause": "<one sentence>",
  "evidence": ["<log line snippet>", ...],
  "confidence": "low | medium | high",
  "next_step": "<one concrete kubectl or curl command>"
}

Constraints:
- If logs are insufficient, set root_cause to "insufficient evidence"
  and list what's missing in evidence.
- Do not invent log lines. Quote them verbatim.
```

The second version isn't longer because it's verbose. It's longer because each part is doing work. Pull any one out and quality drops.

---

## Roles That Actually Help

"You are a helpful assistant" does nothing. The model already thinks that. Useful roles are specific:

- `You are a senior SRE who has been paged at 3 AM and needs to act in 5 minutes.`
- `You are a security reviewer with a checklist. You don't approve anything that isn't on the checklist.`
- `You are a Terraform module author writing for engineers who hate magic.`

The role isn't flattery. It's a steering vector. It shifts the distribution of likely next tokens toward a particular voice and set of priorities.

> **Tip:** Roles that imply *constraints* work better than roles that imply *expertise*. "A reviewer with a checklist" outperforms "an expert reviewer" because checklists are more constraining than expertise.

---

## Structured Output Is Non-Negotiable

If a downstream system is going to read the model's output, free text is a bug. You want JSON, YAML, or another machine-parseable format — and you want to force it.

There are three reliable techniques, in order of strength:

**1. Use the API's structured output feature.**

OpenAI, Anthropic, and Gemini all support schema-constrained outputs now. Use them.

```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class Triage(BaseModel):
    root_cause: str
    confidence: str  # "low" | "medium" | "high"
    next_step: str

resp = client.chat.completions.parse(
    model="gpt-4.1-mini",
    messages=[
        {"role": "system", "content": "You are a senior SRE triaging an incident."},
        {"role": "user", "content": LOG_EXCERPT},
    ],
    response_format=Triage,
)

triage: Triage = resp.choices[0].message.parsed
print(triage.next_step)
```

This is the modern way. The model is *constrained* by the schema during decoding — it cannot return malformed JSON.

**2. Ask for JSON and validate.**

When you can't use structured output (older models, some providers), ask explicitly, then validate:

```python
import json
from pydantic import BaseModel, ValidationError

class Triage(BaseModel):
    root_cause: str
    confidence: str
    next_step: str

prompt = """Return ONLY valid JSON matching this schema:
{"root_cause": str, "confidence": "low"|"medium"|"high", "next_step": str}
Do not include any prose, markdown, or code fences.
"""

raw = call_model(prompt + user_message)
try:
    triage = Triage.model_validate_json(raw)
except ValidationError:
    # Retry once with the error in the prompt
    raw = call_model(prompt + user_message + f"\nPrevious output was invalid: {raw}")
    triage = Triage.model_validate_json(raw)
```

**3. Give an example.**

For models without structured output and for unusual formats:

```
Output format — exactly like this example, no prose around it:

---example---
severity: high
service: payments-api
action: kubectl rollout undo deployment/payments-api -n prod
---end-example---
```

Few-shot examples are the most reliable steering technique that doesn't require API support.

---

## Few-Shot: Show, Don't Just Tell

The model has seen billions of examples during training. A handful of yours during inference shifts behavior more than any amount of instructions.

Use it when:

- The output has a specific style or shape your team uses
- The task is judgment-heavy (severity, priority, tone)
- You've tried instructions and they're inconsistent

Example — commit message normalization:

```
Rewrite each diff summary as a Conventional Commit.

Examples:
  Input:  Added health check endpoint to user service
  Output: feat(user-service): add /health endpoint for load balancer

  Input:  Fixed memory leak in image resize worker
  Output: fix(worker): resolve leak in image resize function

  Input:  Bumped Redis image to 7.2 for CVE patch
  Output: chore(deps): bump redis to 7.2.4 for CVE-2024-31449

Input:  Made the CI pipeline run tests in parallel with cache
Output:
```

Three examples is usually enough. Diminishing returns kick in fast. If five examples don't fix the behavior, the model probably can't do the task with prompting alone.

---

## Chain-of-Thought, Carefully

Asking the model to "think step by step" used to be a magic spell. With modern models it's still useful, but not the way it used to be:

- **Reasoning models** (OpenAI o-series, Claude with extended thinking, Gemini's reasoning models) do this internally. Telling them "think step by step" is redundant and sometimes counterproductive.
- **Non-reasoning models** still benefit from explicit step structure for complex tasks.

When you do want explicit reasoning, structure it. Don't say "think step by step" — say what the steps are:

```
Analyze this Kubernetes pod failure in this order:

1. Read the pod status and most recent event.
2. From the event, identify the failure category:
   image-pull, scheduling, OOMKilled, CrashLoopBackOff, other.
3. Based on the category, list the 2–3 kubectl commands
   most likely to surface the root cause.
4. Output the commands as a numbered list — nothing else.
```

This works better than open-ended "think step by step" because the steps are *yours*, not the model's guess at what reasoning should look like.

---

## Prompt Patterns for DevOps Tasks

These are battle-tested templates. Copy, adapt, ship.

### Log triage

```
ROLE: Senior SRE on incident response.

CONTEXT:
- Service: {service}
- Environment: {env}
- Time window: {start} to {end}
- Recent changes: {recent_deploys_or_configs}

LOGS:
{logs}

TASK: Identify the most likely root cause and the next diagnostic step.

OUTPUT (JSON):
{
  "root_cause": "<one sentence>",
  "evidence_lines": ["<verbatim log line>", ...],
  "confidence": "low|medium|high",
  "next_command": "<one shell or kubectl command>"
}

RULES:
- Quote evidence lines verbatim.
- If the logs do not support a conclusion, set confidence to "low"
  and root_cause to "insufficient evidence: <what's missing>".
```

### Terraform code review

```
ROLE: Platform engineer reviewing infrastructure code for production.

CONTEXT:
- Provider: AWS, region us-east-1
- Compliance: SOC 2, internal tagging policy attached below
- Tagging policy: every resource must have Owner, CostCenter, Environment

CODE:
{terraform_code}

TASK: Review for security, cost, and policy issues. Approve or block.

OUTPUT (JSON):
{
  "decision": "approve | request_changes | block",
  "findings": [
    {"severity": "high|med|low", "line": int, "issue": str, "fix": str}
  ]
}

RULES:
- block on any high-severity finding
- block on missing required tags
- do not invent line numbers — quote them from the provided code
```

### Runbook generation

```
ROLE: Senior SRE writing a runbook for a junior on-call engineer.

CONTEXT:
- System: {system}
- Alert: {alert_name}
- Definition: {alert_definition}

TASK: Write a runbook for responding to this alert.

OUTPUT (Markdown):
# {alert_name}

## What this alert means
<2-3 sentences>

## First 5 minutes
1. <command or check>
2. ...

## Common causes (most likely first)
- **<cause>** — verify with: `<command>`. Fix: `<command>`.

## When to escalate
<concrete criteria>

RULES:
- Every command must be runnable as-is, no placeholders like <pod-name>.
  Use real flags that prompt for input.
- No prose between sections.
```

### Postmortem draft from incident timeline

```
ROLE: Incident commander drafting a blameless postmortem.

CONTEXT:
Timeline (chronological):
{timeline}

Customer impact:
{impact}

TASK: Draft the postmortem in our standard format.

OUTPUT (Markdown headings):
## Summary (3 sentences)
## Impact (numbers, durations, affected services)
## Timeline (copy with minor cleanup)
## Root cause
## What went well
## What went poorly
## Action items (assignee, due date, JIRA-ready)

RULES:
- Blameless. No "X engineer forgot to..." Use "the change did not include..."
- Action items must be specific and bounded. No "improve monitoring."
```

---

## Debugging a Bad Prompt

When a prompt is misbehaving, work through this list in order:

**1. Is the context window full?** Print the actual token count. If history + retrieval is crowding out your instructions, the prompt isn't the problem.

**2. Are your instructions and your example in conflict?** Common: instructions say JSON, the example shows YAML. The example wins. Always.

**3. Are you fighting the model's training?** "Don't apologize" and "don't say 'I'm sorry'" sometimes make models apologize *more* because you've raised the salience of apology. Rephrase positively: "Respond directly with the answer."

**4. Is the task actually ambiguous?** Show the prompt to a teammate. If they can't tell you what the correct output is, the model can't either.

**5. Are you using the wrong model?** A small model with a perfect prompt can still fail. Try the same prompt on a frontier model. If that works, your prompt is fine — you need a bigger model or fine-tuning.

**6. Is temperature too high?** For deterministic tasks (classification, structured extraction), set `temperature=0` or close to it. Default of 1.0 is for creative writing.

---

## A Failure Story

We had a prompt that summarized Slack threads into daily standups. It worked great for a month. Then it started randomly inserting bullet points like "Discussed Q3 OKRs with leadership" — for a team that had never discussed OKRs.

The bug: we were appending the previous day's summary to the prompt as "context." That summary, generated by the model, sometimes contained mild hallucinations. The next day's prompt ingested those hallucinations as fact, amplified them, and fed them back. After two weeks the daily summaries were 30% fiction.

The fix wasn't a better prompt. It was severing the feedback loop. We stopped feeding the model its own outputs as context and started reconstructing context from source (Slack) every time.

The lesson: any LLM output you feed back to an LLM will compound its errors. Always retrieve context from ground truth.

---

## When Prompt Engineering Is the Wrong Answer

Prompts have limits. Reach for one of these when you hit them:

- **The model needs information it doesn't have.** → Retrieval (RAG) or a tool call.
- **The output has to be 100% correct, every time.** → Code, not LLM. Or LLM with deterministic post-validation.
- **The task is the same every time with no judgment.** → Just write the code.
- **The model is consistently bad at this kind of task.** → Different model, or fine-tuning.
- **Your prompt is now 3000 tokens long.** → Probably needs to be split into multiple model calls with their own narrow prompts.

A common pattern in mature systems: small models doing focused tasks, glued together with code. Not one giant prompt asking for everything.

---

## Building a Prompt Library

Once a prompt works, don't lose it. Treat prompts like code:

- Store them in version control, not in someone's notes
- Wrap them in a class or function with a typed input/output
- Write tests with real examples and check outputs against a schema
- Pin the model name and parameters in code, not at call time

A minimal version:

```python
# prompts/triage.py
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class Triage(BaseModel):
    root_cause: str
    confidence: str
    next_command: str

SYSTEM = """You are a senior SRE triaging an incident.
Quote evidence verbatim. If evidence is insufficient, say so."""

def triage_logs(service: str, logs: str) -> Triage:
    resp = client.chat.completions.parse(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Service: {service}\n\nLogs:\n{logs}"},
        ],
        response_format=Triage,
    )
    return resp.choices[0].message.parsed
```

Now the prompt has a version. You can swap the model in one place. You can test it. You can monitor it.

---

## Chapter Summary

- A prompt is the full context the model sees, not just your message.
- Use the five-part structure: role, context, task, format, constraints.
- Force structured output with the API's schema features. Validate.
- Few-shot examples beat instructions for style and judgment tasks.
- Debug in order: context window, conflicts, model, temperature.
- Don't feed model outputs back as context. They compound errors.
- Treat prompts as code. Version them, test them, pin the model.

Next: [AI Tools Integration](04-ai-tools-integration-apis.md) — turning these prompts into running services.

---

## Resources

- [Anthropic — Prompt engineering overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) — the best free resource
- [OpenAI — Prompting guide](https://platform.openai.com/docs/guides/prompt-engineering)
- [OpenAI — Structured outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [The Prompt Report (Schulhoff et al., 2024)](https://arxiv.org/abs/2406.06608) — survey of every prompting technique that's actually been studied

---

[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-red?style=for-the-badge)](https://github.com/sponsors/hoalongnatsu)
