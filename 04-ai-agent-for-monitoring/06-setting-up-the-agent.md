<!-- markdownlint-disable MD041 -->

## 5. Setting Up the Agent

You could build everything from scratch: a log reader with cursor
tracking, a redaction layer, a Drain-style miner, an EWMA baseline, a catalog, an
AI analyzer with caching and rate limits, and a notification pipeline for Slack,
Teams, and PagerDuty. It's a few months of work, and most of it is the boring,
reliability-critical plumbing — not the interesting part.

Don't. The whole point of this book is that you shouldn't have to. Versus Incident
ships the agent in the box, wired into a notification pipeline that already
handles Slack, Teams, Telegram, Email, Lark, PagerDuty, and on-call escalation.
Your job is to turn it on and point it at a log file. This chapter does exactly
that, on your laptop, in a few minutes.

> **The agent is off by default.** Nothing happens until you set
> `agent.enable: true`. Existing Versus users see zero behavior change until they
> opt in.

### What you'll need

- Docker.
- A Redis instance. The agent uses it to track a per-source cursor so a restart
  never replays old logs or skips new ones. For local testing:
  `docker run -d --name versus-redis -p 6379:6379 redis:7`.
- A log file to watch. If you don't have one handy, the repo ships a generator —
  more on that below.

### Step 1 — A working folder

```bash
mkdir -p versus-agent/{config,data,logs}
cd versus-agent
```

- `config/` holds your YAML and mounts to `/app/config` in the container.
- `data/` holds the catalog (`patterns.json`) and other state, and mounts to
  `/app/data`.
- `logs/` is where our sample log file will live.

### Step 2 — The training config

Drop this into `config/config.yaml`. It's the smallest config that does something
useful: read one log file, learn from it, talk to nobody.

```yaml
name: versus
host: 0.0.0.0
port: 3000

alert:
  debug_body: false

queue:
  enable: false
oncall:
  enable: false

redis:
  host: ${REDIS_HOST}
  port: ${REDIS_PORT}
  password: ${REDIS_PASSWORD}
  db: 0

gateway_secret: ${GATEWAY_SECRET}   # any string — you'll use it for the admin UI

storage:
  type: file
  file:
    max_incidents: 1000

agent:
  enable: true
  mode: training          # watch and learn — zero alerts
  poll_interval: 10s
  lookback: 5m

  redaction:
    enable: true          # strip secrets BEFORE anything else sees the line

  catalog:
    persist_interval: 30s
    auto_promote_after: 100   # treat a pattern as "known" after this many sightings

  miner:
    similarity_threshold: 0.4
    tree_depth: 4
    max_children: 100

  regex:
    default_pattern: ".*"     # for the first run, learn from every line
    rules: []
```

The fields that matter most:

- `redaction.enable` runs first in the pipeline. Not optional — this is your
  privacy guarantee.
- `auto_promote_after` is how the agent decides something is normal. See a pattern
  100 times and it's clearly part of your baseline.
- `default_pattern: ".*"` tells the agent to learn from every line during
  training. You'll tighten this later.

And tell it where to read, in `config/agent_sources.yaml`:

```yaml
sources:
  - name: my-app
    type: file
    enable: true
    file:
      path: /app/logs/my-app.log
      format: text
      from_beginning: true
```

Two source types ship today: a **file** reader (shown here — great for testing and
simple setups) and an **Elasticsearch** reader for production clusters. Both
remember where they left off, so a restart never replays or skips.

### Step 3 — Run it

```bash
docker run -d \
  --name versus-agent \
  -p 3000:3000 \
  -v "$PWD/config:/app/config:ro" \
  -v "$PWD/data:/app/data" \
  -v "$PWD/logs:/app/logs:ro" \
  -e AGENT_ENABLE=true \
  -e AGENT_MODE=training \
  -e GATEWAY_SECRET=change-me \
  -e REDIS_HOST=host.docker.internal \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD= \
  ghcr.io/versuscontrol/versus-incident:latest
```

Tail the logs:

```bash
docker logs -f versus-agent
```

You should see the worker start:

```
agent: starting worker mode=training sources=1 poll=10s catalog=/app/data/patterns.json
```

### Step 4 — Give it something to learn

If you don't have real traffic yet, the repo ships a generator that writes
realistic noisy logs — a few dozen common templates (HTTP access lines, GC pauses,
retry warnings) with a sprinkle of rare production weirdness (kernel OOMs,
segfaults, expired TLS, replication lag):

```bash
# write 2000 lines once
python3 scripts/generate_noisy_logs.py \
  --output ./logs/my-app.log \
  --lines 2000 --seed 42

# or stream forever
./scripts/run_noisy_logs.sh \
  --output ./logs/my-app.log \
  --interval 5 --batch 20
```

Within a few ticks you'll see the agent learning:

```
agent: new pattern p-abc123 (source=my-app tag=default) → service=api-gateway method=GET path=<*> status=200 …
agent: tick my-app signals=20 matched=20 patterns=8 verdicts=map[learned:8] cursor=…
```

Each `new pattern` line is a brand-new template the agent just mined. The `<*>`
parts are where it noticed values that change between lines. This is pattern
mining doing the heavy lifting from Chapter 3 — a million log lines collapsing into
a few hundred templates.

### Step 5 — Know when training is done

Two checks:

1. **New patterns should slow to a trickle.** Watch how fast `new pattern` lines
   appear. In the first minutes you'll see many; after a day or two on a small
   service, almost none. New patterns never stop entirely — you won't see every
   variant — but dozens per minute means you haven't trained long enough.
2. **The catalog should plateau.** For a small service the pattern count usually
   levels off in a few days; for a large one, give it a week or two and at least
   one full release cycle. The catalog lives in `data/patterns.json` and survives
   restarts, so you can keep training across redeploys.

That's it. The agent is now reading your logs and building a baseline, and it has
done nothing else — no alerts, no AI calls, no data leaving the box. In the next
chapter we'll open the admin UI and actually *watch* it learn, which is where the
whole thing starts to feel real.

> **A note on production.** The same config scales up: swap the `file` source for
> `elasticsearch`, run the container in Kubernetes, and let a Redis-based leader
> lock ensure only one replica runs the worker (so you don't get duplicate
> incidents from multiple pods). Every external dependency has a fallback: if
> Elasticsearch is down, the agent skips the tick and retries; if the AI provider
> errors, regex and pattern detection keep working; if Redis is unavailable,
> cursors fall back to in-memory state with a warning. Nothing's failure mode is
> "stop working."

**In short:**

- Don't build the plumbing — turn on the agent that ships with Versus Incident.
- Three files get you running: `config.yaml`, `agent_sources.yaml`, and a log
  source. The agent is off until `agent.enable: true`.
- Start in training mode with `default_pattern: ".*"` and let it learn.
- Training is done when new patterns slow to a trickle and the catalog plateaus —
  a few days for a small service, a release cycle for a large one.
