<!-- markdownlint-disable MD041 -->

## 6. Don't Build Your Own

By now you have the two halves of the idea. Chapter 4: keep your runbooks in an
open knowledge format — plain Markdown with a little metadata. Chapter 5:
retrieval by meaning uses embeddings and a similarity search. The obvious next
move is to wire those together: chunk your runbooks, embed them, store the
vectors somewhere, embed each incident, run a similarity search, redact the
query, keep the index fresh as runbooks change…

Stop. That's a project. It's the same project every team rebuilds badly — a
vector database to run, an ingestion pipeline to maintain, a redaction step
someone forgets, an index that silently goes stale. You don't need to build it,
because Versus Incident already did.

**Versus Incident** is an open-source, self-hosted incident tool. Its analyze
agent ships this whole retrieval pipeline as a single tool called `find_runbook`,
and turning it on takes two steps — a config line and a folder. The rest of this
chapter is that simple guide.

### What you're *not* building

It's worth being concrete about what `find_runbook` saves you, because "just use
the tool" undersells it. A hand-rolled runbook-RAG stack means owning all of this:

- An **embedding pipeline** — read files, split them, call an embedding model,
  handle failures and rate limits.
- A **vector store** — stand it up, back it up, keep it in sync with the files.
- A **retrieval path** — embed the incident, run top-K similarity, rank, return.
- A **redaction step** — scrub incident text *before* it's embedded, or you leak
  it to whatever embedding service you use.
- **Incremental reindexing** — notice which runbooks changed and re-embed only
  those, or pay to re-embed everything on every restart.

`find_runbook` is all of that, already built, already tested, and wired straight
into the incident the agent is investigating.

### Step 1 — Configure an embedding model

`find_runbook` registers only when an embedding model is set, so the default
community build is unaffected. In your `tools.yaml`, name the model:

```yaml
tools:
  find_runbook:
    embedding_model: text-embedding-3-small   # empty = tool omitted
```

Two more conditions have to hold, and they're the sensible ones:

- **A storage backend** must be available to persist the embedded corpus (the same
  backend the agent already uses).
- **AI must be enabled** (`AGENT_AI_ENABLE=true`) — `find_runbook` runs inside the
  [AI Analyze](https://docs.versusincident.com/#/agent/ai-analyze-mode) step, and the
  same `agent.ai.api_key` is reused for the embeddings call. One key, one config.

### Step 2 — Drop your runbooks in the corpus

Put your open-format runbooks — the Markdown files from Chapter 4 — in the data
folder under `runbooks/`:

```text
data/
└── runbooks/
    ├── postgres-pool-exhausted.md
    ├── redis-oom.md
    └── api-5xx-spike.md
```

Mount that `data/` folder into the container, and the agent sees the corpus at
`/app/data/runbooks`:

```bash
docker run -d --name versus-incident \
  -p 3000:3000 \
  -v "$PWD/config:/app/config" \
  -v "$PWD/data:/app/data" \
  -e AGENT_ENABLE=true \
  -e AGENT_MODE=detect \
  -e AGENT_AI_ENABLE=true \
  -e AGENT_AI_API_KEY=sk-... \
  ghcr.io/versuscontrol/versus-incident:latest
```

The server **auto-ingests at boot**: it scans the `*.md` files, embeds the ones
that are new or changed, and persists the vectors. On a clean start you'll see it
in the log:

```text
agent: find_runbook: ingested 6 runbook(s) from ./data/runbooks
agent: find_runbook enabled model=text-embedding-3-small runbooks=6
```

That's the whole setup. A config line and a folder. There is no vector database
to run and no pipeline to write.

### It only re-embeds what changed

Ingestion is **incremental**, which matters more than it sounds. A runbook whose
content hasn't changed since the last boot reuses its cached embedding — so
restarting with no edits makes *zero* embedding calls, and costs nothing. Edit one
runbook, and only that one is re-embedded on the next boot. You get a corpus
that's always current without paying to rebuild it every time the container
restarts.

### What happens at incident time

You don't call `find_runbook` yourself — the analyze agent does, when it decides a
finding needs your team's steps. It builds a short natural-language query from the
incident, and — this is the important part — **the query is scrubbed through the
redactor before it is embedded.** Then it runs a top-K similarity search over your
corpus and gets back ranked matches: each with the runbook's `id`, `title`,
`service`, a similarity `score`, and a bounded `excerpt` of the body. It can also
scope to a single `service`, which is exactly why you set that front-matter field
in Chapter 4.

The tool is **search-only.** It reads and ranks runbooks. It never runs a
remediation, never triggers on-call, never sends a notification. The agent reads
your runbook; a human still runs it. And every call — the query and what it
returned — is recorded in the **Tool calls** section of the analysis, so you can
audit exactly which runbook backed a finding. (We'll walk a full incident
through it in the next chapter.)

### The rest is there when you need it

Two conveniences worth knowing about now:

- **Manage runbooks from the admin UI.** Beyond the corpus folder, you can upload,
  view, and delete runbooks from the Runbooks page. Uploads rebuild the search
  index atomically, so a new runbook becomes searchable without a restart.
- **Pre-bake the corpus for CI or air-gapped builds.** You usually don't need it —
  the server ingests at boot — but a `runbook-ingest` command builds the corpus
  out-of-band so an image starts with it already populated. It reads the same
  runbooks directory, the same embedding model, and the same key the server uses.

### The trade you're making

Building your own retriever means you control every knob and own every failure.
Using `find_runbook` means you write a config line, drop in a folder of Markdown,
and inherit a redaction step, an incremental index, an audit trail, and a
self-hosted path you didn't have to design. For nearly every team, that trade is
obvious — the retriever was never the interesting part. Your runbooks are.

Next, we'll follow a real incident from an unfamiliar error line all the way to a
finding that cites your own remediation steps — and see `find_runbook` do its one
job in context.
