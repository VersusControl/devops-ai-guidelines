<!-- markdownlint-disable MD041 -->

## 7. Using Runbooks in a Live Incident

Everything so far has been setup: runbooks in an open format, made searchable by
meaning, with a retriever you didn't have to build. This chapter is the payoff —
watching it work on a real incident, end to end, so you can see exactly what the
engineer on-call experiences.

### The incident

It's a normal evening. The `api` service starts erroring, and Versus opens an
incident:

> **Incident:** `api` — `FATAL: remaining connection slots are reserved for
> non-replication superuser connections`, error rate climbing.

This is a known failure — your team has seen connection-pool exhaustion before, and
someone wrote a runbook for it months ago. In the old world, this is where the
scramble starts: which wiki, which words, does a runbook even exist. Here, it
doesn't.

### The agent reaches for your knowledge

As the analyze agent investigates, it decides the finding needs your team's actual
remediation steps — not generic advice about Postgres it invented. So it calls
`find_runbook`, building the query from the incident itself:

```json
{
  "tool": "find_runbook",
  "args": {
    "query": "postgres connection slots reserved, pool exhausted on api",
    "service": "api",
    "limit": 3
  }
}
```

Two things are happening here that matter. First, it **scoped to `service: api`**,
so the search only considers runbooks that apply to the service on fire — the
`service` front-matter you set back in Chapter 4, paying off. Second — and this is
the non-negotiable one — **the query is scrubbed through the redactor before it is
embedded.** The incident text may carry sensitive strings; they're removed before
anything leaves for the embedding model. (Chapter 8 is entirely about this
guarantee.)

### The match

The tool embeds the query, runs the similarity search over your corpus, and returns
ranked matches:

```json
{
  "tool": "find_runbook",
  "found": true,
  "data": {
    "count": 1,
    "service": "api",
    "matches": [
      {
        "id": "postgres-pool-exhausted.md",
        "title": "Postgres connection pool exhausted",
        "service": "api",
        "score": 0.89,
        "excerpt": "1. Check active connections: SELECT count(*) FROM pg_stat_activity; 2. Terminate stuck idle-in-transaction sessions. 3. Roll back the most recent api deploy if the leak is app-side."
      }
    ]
  }
}
```

Notice the match landed — `score: 0.89` — even though the incident said "connection
slots reserved" and the runbook is titled "pool exhausted." That's the semantic
retrieval from Chapter 5 doing its one job: it matched by meaning, not by keyword.

### The finding cites *your* steps

The agent folds those steps into its conclusion. Instead of a generic "you may be
experiencing connection pool exhaustion; consider increasing max_connections," the
finding says, in effect: *this looks like the connection-pool exhaustion your team
has a runbook for — check `pg_stat_activity`, terminate idle-in-transaction
sessions, and roll back the last `api` deploy if the leak is app-side.* Your real
commands. Your real decision about rolling back. The exact procedure the person who
wrote it trusted.

The engineer opens the incident and the fix is already there — cited, scoped to the
right service, backed by the team's own knowledge — without having searched a
single wiki. Compare that to the scramble in Chapter 2. Same failure. A
completely different night.

### It's read-only, and it's on the record

Two properties keep this trustworthy:

- **Search-only.** `find_runbook` reads and ranks. It never runs a remediation,
  never triggers on-call, never sends a notification. It surfaced your runbook; a
  human still runs the steps. The agent brought the knowledge; it did not act on it.
- **Audited.** The call — its arguments and what it returned — is recorded in the
  **Tool calls** section of the analysis. You can see, after the fact, exactly which
  runbook backed the finding. When someone asks “why did the agent say that,”
  there's a receipt.

### When nothing matches

Sometimes there's no runbook for a failure — it's genuinely new, or you simply
haven't written one yet. When nothing matches (or the corpus is empty), the tool
returns `found: false` with an empty list, and **the analysis still completes.** It
just proceeds without a cited runbook, exactly as it would on a build with no
runbooks at all. Retrieval is an enhancement, never a dependency; a missing runbook
degrades the finding, it doesn't break the incident.

That gap — "no runbook matched" — is also the most useful signal your knowledge base
gives you. It's a to-do: write the runbook, so next time it's there. Which brings us,
after one chapter on privacy, to keeping the whole thing alive.
