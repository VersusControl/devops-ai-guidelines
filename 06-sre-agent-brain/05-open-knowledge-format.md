<!-- markdownlint-disable MD041 -->

## 4. Open Knowledge Format

In the last chapter we drew the line: a runbook is knowledge to retrieve, not a
document to read later. This chapter is about the shape that knowledge has to
take for retrieval to work — and the good news is that it's a shape you almost
certainly already write in, and that now has a name and a written spec.

That spec is the **Open Knowledge Format (OKF)** — an open, vendor-neutral
standard Google Cloud published in 2026. It gives a name to the pattern teams kept reinventing: store knowledge as a directory of plain Markdown files, each with a small block of YAML metadata on top.

### What OKF actually is

OKF is deliberately minimal. Three ideas carry the whole format:

- **A bundle is a directory of Markdown files.** The directory *is* the knowledge
  base — the unit you version, diff, and ship. OKF calls it a **bundle**.
- **Each file is one "concept."** One Markdown file per unit of knowledge — for us,
  one runbook per failure mode. The file opens with a YAML **frontmatter** block
  (delimited by `---`), and everything below is the human-readable body.
- **Exactly one field is required: `type`.** It names what kind of concept the file
  is — `Runbook`, `Playbook`, `Metric`, `Table`. Everything else — `title`,
  `description`, `tags`, and any key you invent — is optional, and a well-behaved
  reader must not choke on a field or a `type` it doesn't recognize.

Two filenames are reserved: `index.md` (an optional directory listing) and `log.md`
(an optional change history). Concepts can point at each other with ordinary
Markdown links, which turns a folder of files into a small knowledge *graph*. That's
the entire format. It's boring on purpose: the more exotic the format, the fewer
tools can read it and the sooner it rots.

### Why the wiki fails this test

Most teams keep runbooks in a wiki — Confluence, Notion, a SharePoint, an
internal portal. Those are fine for humans and terrible for machines. The content
lives behind an API, in a format you don't control, tangled with rendering
metadata. You can't `git diff` it. You can't easily hand the raw text to a
retriever. And when you want to move off the tool, you export a zip of HTML and
spend a weekend cleaning it up.

A runbook in an open knowledge format has the opposite properties. It's a file.
You can read it in a terminal, diff it in a PR, grep it, embed it, and move it to
a new tool by copying a folder. The knowledge outlives whatever software you're
using this year.

### A runbook as an OKF concept

A runbook is an OKF concept: a **Markdown file** that opens with a small
YAML **frontmatter** block, with the human body — the steps your team actually
runs — below it.

```markdown
---
type: Runbook
title: Postgres connection pool exhausted
service: api
tags: [database, postgres]
---
# Postgres connection pool exhausted

1. Check active connections: `SELECT count(*) FROM pg_stat_activity;`
2. Terminate stuck idle-in-transaction sessions.
3. Roll back the most recent api deploy if the leak is app-side.
```

That's a complete, valid runbook — and a conformant OKF concept. Two audiences read
the same file:

- **A human** reads the body — the numbered steps, the exact SQL, the decision
  about rolling back.
- **A machine** reads the frontmatter to know *what this runbook is about* and the
  body to build a searchable representation of *what it says*.

One file, both jobs. You never maintain a separate "index" or "tags database" —
the metadata rides with the content, so it can't drift out of sync.

### Your runbooks are a bundle

A single runbook is one concept. Your knowledge base is the **bundle** — the
`runbooks/` directory that holds them:

```text
data/runbooks/
├── postgres-pool-exhausted.md
├── redis-oom.md
└── api-5xx-spike.md
```

Three failure modes, three files, one folder you own and keep in git. Each file is
a self-contained OKF concept — `type: Runbook`, a `title`, a `service`, and the real
remediation steps in the body. This is the exact bundle we'll hand to the retriever
in the next chapter and watch it pick the right file for a live `api` incident.

### The metadata that matters

OKF requires only `type`. Every other field is optional — and each earns its place
by making a runbook more findable:

| Field | Required? | Purpose |
|---|---|---|
| `type` | Yes (OKF) | The kind of concept. Use `type: Runbook`. A retriever works with or without it, but setting it keeps the file conformant and portable to any OKF tool. |
| `title` | No | The display name. If you omit it, it falls back to the first `# ` heading, then the filename — so you're never forced to repeat yourself. |
| `service` | No | The one service this runbook applies to. This is the high-leverage one: it lets a retriever *scope* a search to the runbooks that apply to the service that's on fire. (A producer-defined extension key.) |
| `services` | No | A list, for a runbook that covers several services at once. |
| `tags` | No | Free-form labels for your own organization — `database`, `network`, `payments`. |

The single highest-leverage thing you can do is set `service` (or `services`).
When an incident is on `api`, a `service: api` filter keeps the search focused on
runbooks that apply — so a database runbook for `payments` never crowds out the
right one. It's a small amount of typing that pays off every time the pager
fires.

### Writing runbooks that retrieve well

The format is easy. Writing runbooks the retriever can actually match takes a
little care — none of it exotic:

- **One runbook per file.** A single Markdown file per failure mode. Don't pack
  ten unrelated procedures into one mega-page; the retriever returns whole
  runbooks, and a focused file matches a focused incident.
- **Name the symptom, not just the fix.** The retriever matches your runbook
  against the *incident* — error messages, symptoms, service names. A runbook
  titled "Postgres connection pool exhausted" with the real error text in the body
  matches an incident that says `remaining connection slots are reserved`. A
  runbook titled "DB Playbook v3" matches nothing.
- **Put the real words in the body.** The commands, the error strings, the service
  names your logs actually emit. That concrete text is what makes the match land.
- **Scope with `service`.** As above — it's the cheapest accuracy you'll ever buy.
- **Keep it in git.** Review runbook changes like code. A runbook that goes through
  a PR stays current; one that lives in a wiki nobody edits goes stale.

### Why this is worth doing even without an agent

Here's the quiet payoff: an open knowledge format is *not a bet on any one tool.*
Because your runbooks are plain Markdown files in your own repo, they're already
useful with nothing else — a human can open one and follow it. Adding an agent on
top doesn't change the format or lock you in; it just makes the same files
searchable by meaning. And if you ever switch tools, you move a folder. The
knowledge is yours, in a form that outlives the software.

That's the whole idea behind OKF: write the fix down once, in the open, so both
your teammates and your agent can use it — today, and after the next tool
migration.

In the next chapter we'll take exactly this bundle — those three files — and watch
a machine "read" the bodies to find the right runbook by meaning: embeddings and
similarity search, without the math.
