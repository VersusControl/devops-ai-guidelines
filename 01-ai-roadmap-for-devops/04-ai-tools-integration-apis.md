# AI Tools Integration — APIs and Automation

*Phase 1, chapter 4 — turning AI APIs into running DevOps services.*

> ⭐ Star this repo if you find it useful.

---

## Why This Chapter Exists

By now you can call an LLM from a Python script. That's not the same as having an AI tool in production. Production means: it survives bad inputs, it doesn't bankrupt you when traffic spikes, it doesn't leak secrets, and someone other than you can run it at 3 AM.

This chapter walks through how to wire LLM APIs into real DevOps work. The running example is a CloudWatch log analyzer — fetch logs, ask an LLM to triage them, post structured alerts to Slack. It's small enough to fit in a chapter and realistic enough to ship.

By the end you'll have:

- A multi-provider AI client with rate limiting and cost tracking
- A working CloudWatch analyzer using the modern OpenAI SDK
- A pattern you can reuse for other "fetch data → LLM → act" pipelines

---

## What "Production-Ready" Actually Means

People throw this phrase around. Here's what I mean by it:

1. **Secrets aren't hardcoded.** API keys come from environment variables, Vault, AWS Secrets Manager — anywhere except your repo.
2. **Failures don't crash the caller.** Network blip, rate limit, malformed JSON from the model — none of these should take the service down.
3. **Cost is observable.** Every call's tokens and dollar cost get tracked. You find out about a runaway loop in minutes, not at month-end.
4. **Outputs are validated.** The model returns JSON? You parse it with a schema and reject bad responses, not just `json.loads` and pray.
5. **It can be paused.** A kill switch — environment variable, feature flag, whatever — that disables AI calls without redeploying.

If your code doesn't do all five, it's a prototype. Which is fine, as long as you call it that.

---

## Setting Up the Environment

Pin the versions. The SDKs change.

```bash
pip install \
  "openai>=1.50,<2.0" \
  "anthropic>=0.40" \
  "google-genai>=1.0" \
  "boto3>=1.34" \
  "pydantic>=2.7" \
  "tenacity>=8.5" \
  "python-dotenv>=1.0"
```

A note on the Google SDK: the old package was `google-generativeai`. It's been replaced by `google-genai`, which is what you want. If a tutorial imports `google.generativeai`, it's outdated.

Credentials in `.env` (never commit this file):

```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
AWS_REGION=us-east-1
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

Load it once at startup:

```python
# config.py
from dotenv import load_dotenv
load_dotenv()
```

---

## A Multi-Provider AI Client

Most teams need to talk to more than one provider — for fallback, cost optimization, or because different models are better at different things. The right abstraction is small: one function that returns a string (or a parsed object), with provider details hidden.

Here's the whole thing. Save as `ai_client.py`.

```python
# ai_client.py
from __future__ import annotations
import os
import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Literal, Type, TypeVar
from collections import deque

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from google import genai as google_genai
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

Provider = Literal["openai", "anthropic", "google"]


@dataclass
class Usage:
    """Per-call usage record."""
    provider: Provider
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_s: float


# Prices in USD per 1M tokens (mid-2026). Update from each provider's pricing page.
PRICING = {
    "gpt-4.1":         {"input": 2.00,  "output": 8.00},
    "gpt-4.1-mini":    {"input": 0.15,  "output": 0.60},
    "gpt-5":           {"input": 10.00, "output": 30.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-opus-4":   {"input": 15.00, "output": 75.00},
    "gemini-2.5-pro":  {"input": 1.25,  "output": 5.00},
    "gemini-2.5-flash":{"input": 0.075, "output": 0.30},
}


def _compute_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    p = PRICING.get(model)
    if not p:
        return 0.0
    return (in_tokens * p["input"] + out_tokens * p["output"]) / 1_000_000


class TokenBucket:
    """Simple per-minute request limiter. Async-safe."""
    def __init__(self, requests_per_minute: int):
        self.limit = requests_per_minute
        self.calls: deque[float] = deque()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self.lock:
            now = time.monotonic()
            while self.calls and now - self.calls[0] > 60:
                self.calls.popleft()
            if len(self.calls) >= self.limit:
                wait = 60 - (now - self.calls[0])
                log.info("rate limit: sleeping %.2fs", wait)
                await asyncio.sleep(wait)
            self.calls.append(time.monotonic())


class AIClient:
    """Thin wrapper over OpenAI, Anthropic, and Google Gemini."""

    def __init__(self, requests_per_minute: int = 60):
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # google-genai picks up GOOGLE_API_KEY from env
        self.google = google_genai.Client()
        self.limiter = TokenBucket(requests_per_minute)
        self.history: list[Usage] = []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def complete(
        self,
        *,
        provider: Provider,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> tuple[str, Usage]:
        await self.limiter.acquire()
        start = time.perf_counter()

        if provider == "openai":
            resp = await self.openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = resp.choices[0].message.content or ""
            in_tok = resp.usage.prompt_tokens
            out_tok = resp.usage.completion_tokens

        elif provider == "anthropic":
            resp = await self.anthropic.messages.create(
                model=model,
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = resp.content[0].text
            in_tok = resp.usage.input_tokens
            out_tok = resp.usage.output_tokens

        elif provider == "google":
            # google-genai is sync; run in a thread to keep async semantics
            def _call():
                return self.google.models.generate_content(
                    model=model,
                    contents=user,
                    config={
                        "system_instruction": system,
                        "max_output_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
            resp = await asyncio.to_thread(_call)
            content = resp.text or ""
            in_tok = resp.usage_metadata.prompt_token_count
            out_tok = resp.usage_metadata.candidates_token_count

        else:
            raise ValueError(f"unknown provider: {provider}")

        usage = Usage(
            provider=provider,
            model=model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=_compute_cost(model, in_tok, out_tok),
            latency_s=round(time.perf_counter() - start, 3),
        )
        self.history.append(usage)
        log.info(
            "%s/%s in=%d out=%d cost=$%.4f t=%.2fs",
            provider, model, in_tok, out_tok, usage.cost_usd, usage.latency_s,
        )
        return content, usage

    async def complete_structured(
        self,
        *,
        schema: Type[T],
        model: str,
        system: str,
        user: str,
        temperature: float = 0.0,
    ) -> tuple[T, Usage]:
        """OpenAI-only convenience: schema-constrained output."""
        await self.limiter.acquire()
        start = time.perf_counter()
        resp = await self.openai.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format=schema,
        )
        parsed = resp.choices[0].message.parsed
        in_tok = resp.usage.prompt_tokens
        out_tok = resp.usage.completion_tokens
        usage = Usage(
            provider="openai",
            model=model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=_compute_cost(model, in_tok, out_tok),
            latency_s=round(time.perf_counter() - start, 3),
        )
        self.history.append(usage)
        return parsed, usage

    @property
    def total_cost(self) -> float:
        return sum(u.cost_usd for u in self.history)
```

What this gives you:

- **One interface** for three providers. Swap models by changing a string.
- **Retries** for transient failures (network, timeout). Not for everything — if the model returns bad JSON, retrying won't help.
- **Rate limiting** at the client level. You won't hammer the provider into 429s.
- **Cost tracking** by call. Sum it whenever you want.
- **Schema-constrained outputs** for OpenAI via `complete_structured`.

What it deliberately doesn't do:

- Streaming. Add it when you need it.
- Caching. Same.
- Multi-region failover. Provider-level concern; most teams don't need it.

> **Warning:** Don't paper over real errors with retries. If you keep getting 401s, retrying just generates more failed bills. Retry only on `TimeoutError` and `ConnectionError`. Let other exceptions bubble up.

---

## The CloudWatch Log Analyzer

Now build something with it. Goal: pull recent logs from a CloudWatch log group, ask the model to triage them, post a structured alert if anything bad shows up.

### IAM permissions

Least privilege. Read-only:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "logs:DescribeLogStreams",
      "logs:FilterLogEvents",
      "logs:GetLogEvents"
    ],
    "Resource": "arn:aws:logs:*:*:log-group:/aws/*:*"
  }]
}
```

Scope the `Resource` to the specific log groups you actually need. Wildcards in production IAM are how you end up in a security review.

### The triage schema

Define the output shape first. Pydantic enforces it.

```python
# schemas.py
from typing import Literal
from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "none"]

class ErrorPattern(BaseModel):
    pattern: str = Field(..., description="Short label for this error class")
    count: int = Field(..., ge=0)
    sample: str = Field(..., description="One log line, verbatim")

class Action(BaseModel):
    priority: Literal["high", "medium", "low"]
    description: str
    command: str | None = Field(None, description="Shell command if applicable")

class Triage(BaseModel):
    severity: Severity
    summary: str = Field(..., description="One sentence")
    error_patterns: list[ErrorPattern] = Field(default_factory=list)
    likely_causes: list[str] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
```

The schema is documentation. A teammate can read it and know exactly what the analyzer returns without running it.

### Fetching logs

CloudWatch's API is fiddly. Times are in milliseconds since epoch. Streams need to be discovered first.

```python
# cloudwatch.py
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)


class CloudWatchReader:
    def __init__(self, region: str = "us-east-1"):
        self.client = boto3.client("logs", region_name=region)

    async def fetch_recent(
        self,
        log_group: str,
        *,
        minutes: int = 10,
        filter_pattern: str = "",
        max_events: int = 1000,
    ) -> list[dict]:
        """Return raw log events from the last `minutes`."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=minutes)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)

        def _filter():
            params = {
                "logGroupName": log_group,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": min(max_events, 10_000),
            }
            if filter_pattern:
                params["filterPattern"] = filter_pattern
            try:
                return self.client.filter_log_events(**params).get("events", [])
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == "ResourceNotFoundException":
                    log.error("log group not found: %s", log_group)
                    return []
                raise

        return await asyncio.to_thread(_filter)

    @staticmethod
    def format(events: list[dict], max_chars: int = 12_000) -> str:
        """Render events as a chronological text block, truncated to fit context."""
        events = sorted(events, key=lambda e: e["timestamp"])
        lines: list[str] = []
        used = 0
        for ev in events:
            ts = datetime.fromtimestamp(ev["timestamp"] / 1000, tz=timezone.utc)
            line = f"{ts.strftime('%H:%M:%S')} {ev['message'].rstrip()}"
            if used + len(line) > max_chars:
                lines.append(f"... [{len(events) - len(lines)} more events truncated]")
                break
            lines.append(line)
            used += len(line) + 1
        return "\n".join(lines)
```

Note `datetime.now(timezone.utc)` — `datetime.utcnow()` was deprecated in Python 3.12 because it returns naive datetimes that silently mislead anyone working across timezones.

`asyncio.to_thread` wraps boto3's sync calls so they don't block the event loop. Boto3 doesn't have a real async client; this is the standard workaround.

### Putting it together

```python
# analyzer.py
from __future__ import annotations
import asyncio
import json
import logging
import os

import httpx

from ai_client import AIClient
from cloudwatch import CloudWatchReader
from schemas import Triage

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior SRE triaging CloudWatch logs.
- Quote evidence verbatim. Do not invent log lines.
- If logs do not support a conclusion, set severity to "none"
  and confidence to "low".
- Commands in actions must be runnable as-is."""


class LogAnalyzer:
    def __init__(
        self,
        ai: AIClient,
        reader: CloudWatchReader,
        model: str = "gpt-4.1-mini",
        slack_webhook: str | None = None,
    ):
        self.ai = ai
        self.reader = reader
        self.model = model
        self.slack_webhook = slack_webhook or os.getenv("SLACK_WEBHOOK_URL")

    async def analyze(
        self,
        log_group: str,
        *,
        minutes: int = 10,
        filter_pattern: str = "ERROR",
    ) -> Triage | None:
        events = await self.reader.fetch_recent(
            log_group, minutes=minutes, filter_pattern=filter_pattern
        )
        if not events:
            log.info("no events in %s for the last %d minutes", log_group, minutes)
            return None

        logs_text = self.reader.format(events)
        user_msg = (
            f"Log group: {log_group}\n"
            f"Window: last {minutes} minutes\n"
            f"Filter: {filter_pattern or '(none)'}\n\n"
            f"--- logs ---\n{logs_text}\n--- end logs ---"
        )

        triage, usage = await self.ai.complete_structured(
            schema=Triage,
            model=self.model,
            system=SYSTEM_PROMPT,
            user=user_msg,
        )
        log.info("triaged %s: severity=%s cost=$%.4f", log_group, triage.severity, usage.cost_usd)
        return triage

    async def notify(self, log_group: str, triage: Triage) -> None:
        if triage.severity in ("none", "low"):
            return
        if not self.slack_webhook:
            log.warning("no SLACK_WEBHOOK_URL configured; would have sent: %s", triage.summary)
            return

        color = {"critical": "#FF0000", "high": "#FF8800", "medium": "#FFCC00"}[triage.severity]
        payload = {
            "attachments": [{
                "color": color,
                "title": f"[{triage.severity.upper()}] {log_group}",
                "text": triage.summary,
                "fields": [
                    {"title": "Confidence", "value": triage.confidence, "short": True},
                    {"title": "Top action",
                     "value": triage.actions[0].description if triage.actions else "n/a",
                     "short": False},
                ],
            }]
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(self.slack_webhook, json=payload)
            r.raise_for_status()


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ai = AIClient(requests_per_minute=60)
    reader = CloudWatchReader(region=os.getenv("AWS_REGION", "us-east-1"))
    analyzer = LogAnalyzer(ai, reader, model="gpt-4.1-mini")

    triage = await analyzer.analyze(
        log_group="/aws/lambda/payments-api",
        minutes=15,
        filter_pattern="ERROR",
    )
    if triage:
        print(json.dumps(triage.model_dump(), indent=2))
        await analyzer.notify("/aws/lambda/payments-api", triage)
    print(f"\ntotal spend this run: ${ai.total_cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
```

That's the whole thing. Three files, plus the schema. Run it:

```bash
python analyzer.py
```

Output looks like:

```json
{
  "severity": "high",
  "summary": "Multiple Stripe webhook signature validation failures starting 09:14 UTC",
  "error_patterns": [
    {"pattern": "InvalidSignature", "count": 47,
     "sample": "09:14:23 ERROR stripe.webhook InvalidSignature: ..."}
  ],
  "likely_causes": [
    "STRIPE_WEBHOOK_SECRET environment variable was rotated and not redeployed"
  ],
  "actions": [
    {"priority": "high",
     "description": "Verify STRIPE_WEBHOOK_SECRET matches Stripe dashboard",
     "command": "aws secretsmanager get-secret-value --secret-id payments/stripe-webhook"}
  ],
  "confidence": "medium"
}
```

---

## Running It on a Schedule

The analyzer is one shot. To monitor continuously, run it from whatever scheduler you already have:

**Cron, for the smallest version:**

```bash
*/5 * * * * cd /opt/analyzer && /opt/venv/bin/python analyzer.py >> /var/log/analyzer.log 2>&1
```

**Lambda + EventBridge** for AWS-native:

```python
# lambda_handler.py
import asyncio
import os
from analyzer import LogAnalyzer
from ai_client import AIClient
from cloudwatch import CloudWatchReader

def handler(event, context):
    log_group = event.get("log_group") or os.environ["LOG_GROUP"]
    analyzer = LogAnalyzer(AIClient(), CloudWatchReader())
    triage = asyncio.run(analyzer.analyze(log_group, minutes=15))
    if triage:
        asyncio.run(analyzer.notify(log_group, triage))
    return {"severity": triage.severity if triage else "none"}
```

**Kubernetes CronJob** if you live there. Same pattern, different YAML.

The point: don't build a service if you don't need one. A 5-minute cron with the right output is fine.

---

## Cost, Observed

A single `gpt-4.1-mini` call on ~10K characters of logs costs roughly $0.001–$0.002 in mid-2026 prices. Running every 5 minutes against one log group: about $0.50/day, or $15/month per group.

A team I work with monitors 40 log groups this way. They spend about $20/day on the LLM. The first month they ran it, it caught a misrouted Slack webhook that had been silently dropping incident notifications for a week. Easy ROI.

The mistake people make: defaulting to `gpt-5` or `claude-opus-4` for this. Those are 30x the cost. Triage is a workhorse task; use a workhorse model.

---

## A Failure Story

The first version of this analyzer didn't truncate logs. It just stuffed everything into the prompt. Worked great on small log groups. The day someone pointed it at `/aws/ecs/web-frontend` — which produces 200K events per hour — the bill for the day was $340.

Two bugs caused that:

1. No truncation. We sent the model 800KB of logs in one call.
2. No cost ceiling. The script ran on a cron with no daily budget.

Both fixes are in the code above. `format()` truncates at 12K chars. `AIClient.total_cost` lets you bolt on a kill switch:

```python
if ai.total_cost > 5.00:
    log.critical("daily budget exceeded; aborting")
    raise SystemExit(1)
```

That's not a paranoid check. It's the difference between a $15 month and a $340 day.

---

## Where to Go From Here

You now have the pattern. Variations:

- **Replace CloudWatch with anything.** Datadog logs, Loki, Elasticsearch — change the reader, keep the rest.
- **Replace Slack with PagerDuty.** Change `notify()`, keep the rest.
- **Add a fallback model.** Wrap `complete_structured` in a try/except; on failure call Anthropic.
- **Add deduplication.** Hash the triage summary, skip notifying if the same alert fired in the last hour.

What you should *not* do yet:

- Build a UI for it. CLI output and Slack are enough.
- Make the LLM "act on" logs autonomously. Read-only is the safe place to start.
- Turn this into an agent loop with multiple tools. That's the next chapter.

---

## Chapter Summary

- One small client class handles three providers cleanly.
- Use structured outputs when the API supports them. Validate with Pydantic when it doesn't.
- Boto3 is sync; wrap it with `asyncio.to_thread`.
- Truncate context before it eats your budget. Always have a cost ceiling.
- The right default model for triage is the workhorse tier, not the frontier.
- Don't ship a service when a cron job will do.

Next: [MCP — Model Context Protocol](05-01-mcp-model-context-protocol.md) — the protocol that lets the model call your tools instead of just reading data.

---

## Resources

- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [google-genai (new Gemini SDK)](https://github.com/googleapis/python-genai)
- [Boto3 CloudWatch Logs API](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/logs.html)
- [tenacity — retry library](https://tenacity.readthedocs.io/)

---

[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-red?style=for-the-badge)](https://github.com/sponsors/hoalongnatsu)
