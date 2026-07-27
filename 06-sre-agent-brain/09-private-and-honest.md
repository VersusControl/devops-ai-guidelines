<!-- markdownlint-disable MD041 -->

## 8. Keeping It Private and Verifiable

There's a fair question hanging over everything in this book. To make your runbooks
searchable by meaning, you embed text — you send it to a model that turns it into
coordinates. And to retrieve during an incident, you embed a query built from that
incident. So: **where does that text go, and what's in it?**

For a lot of teams — regulated, security-sensitive, or just careful — this is the
question that decides whether any of this is usable at all. Here are the straight
answers.

### Redaction runs before the text is ever embedded

The query the agent builds from an incident can carry incident-derived text, and
incident-derived text can carry secrets. So embedding a query is treated as exactly
what it is: an external trust boundary, the same as any call that leaves your
process.

That means the query is **scrubbed through the same redactor before it is
embedded** — the identical `redaction.*` machinery Versus uses everywhere else, the
one that strips tokens, keys, emails, and the patterns you configure. And the
returned excerpts are scrubbed again on the way out. Incident-derived text never
egresses raw. This isn't a policy note in a doc; it's a step in the code path, on
the same footing as the redaction that guards every other outbound call.

### You can keep the embeddings inside your own network

Redaction protects the *content* of the query. If you don't want the text leaving
your infrastructure **at all** — not even redacted — you don't have to send it out.

The embedder follows the same provider as the chat path. Point `agent.ai.provider`
at a self-hosted option — `ollama`, for instance — and the embedding calls run
inside your own network. No code change, no separate configuration for the embedder;
it inherits the provider you already chose. Your runbooks are embedded, your queries
are embedded, and none of it touches a third party. Self-hosted all the way down.

### Your knowledge stays yours

The rest follows from the format. Your runbooks are plain Markdown files in your own
repo (Chapter 4). The embedded corpus persists to the same storage backend Versus
already uses — your storage, in your infrastructure. There's no runbook SaaS in the
loop, nothing phones home, and if you walk away from the tool you walk away with your
files intact. The knowledge was never anywhere you didn't control.

### Verifiable by construction

A few properties from earlier chapters are worth collecting here, because together
they're what make the feature trustworthy rather than merely capable:

- **Search-only.** `find_runbook` reads and ranks. It never executes a remediation,
  never pages, never notifies. It cannot take an action, so it cannot take a wrong
  one.
- **Audited.** Every call and its result land in the analysis's **Tool calls**
  trail. Which runbook backed which finding is a matter of record, not trust.
- **Graceful.** No match means the analysis proceeds without a cited runbook. Retrieval
  never becomes a single point of failure for the incident.

None of these are promises in marketing copy. They're behaviors you can read in the
tool and confirm in the audit trail.

### The open-core line, stated plainly

To be straight about what's free and what isn't: the runbook brain itself — the
store, the embedding seam, the search index, the `find_runbook` tool, and the
ingestion — lives in the open-source core and is fully useful single-tenant. It's
the whole system this book describes, and it's MIT-licensed. What the Enterprise
tier adds on top is the org-scaling layer: per-organization isolation of the corpus
and a hosted, scalable vector backend for teams that need it. Nothing in the core is
held back to force the upgrade — the free version is the real thing, and this book
runs entirely on it.

Privacy handled, we can spend the last chapter on the ongoing work: keeping the
knowledge base fresh enough that the agent never cites a fix that no longer works.
