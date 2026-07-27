<!-- markdownlint-disable MD041 -->

## Introduction

Every team has the other story — not the one about the failure nobody saw
coming, but the one about the failure you'd seen before. The incident fires.
Someone in the channel says, "we have a runbook for this." And then 20
minutes go by while three people search a wiki, a git repo, and an old Slack
thread for a document that definitely exists, somewhere, in some version. By the
time you find it — or give up and rebuild the fix from memory — the outage has
already cost you what it was going to cost.

That gap — between "the answer exists" and "the answer is in front of the person
who needs it" — is the subject of this book. Not because writing runbooks is
wrong. Runbooks are some of the most valuable work an on-call team does. The
problem is structural: **a runbook you can't find in the moment is worth exactly
as much as a runbook you never wrote.** Your team's hard-won operational
knowledge is real, and it's already written down. It just isn't *reachable* when
the pager goes off.

There's a single reframe at the center of everything here:

> A runbook isn't a document you read later. It's knowledge you retrieve *now* —
> the instant an incident fires.

Once you take that seriously, the job changes. It's no longer "write more
runbooks" or "reorganize the wiki again." It's: keep your knowledge in a form you
own and can search by *meaning*, and put a retriever in front of it that runs
automatically, at 3 a.m., without a human remembering the right search term.

This is not a new idea. Support teams, legal teams, and search engines have
turned piles of documents into instant answers for years. What's newer is
pointing that same machinery at your runbooks and wiring it into the incident
your agent is already investigating — so the fix your team wrote last quarter
shows up, cited, in the analysis of tonight's page.

### What you'll build

By the end of this book you'll have a working system that:

- Keeps your runbooks as **open, plain-text knowledge** — Markdown files with a
  little structured metadata — that you own, version in git, and can move
  anywhere. No proprietary wiki, no lock-in.
- Makes that knowledge **searchable by meaning**, not just keywords, so the right
  runbook surfaces even when the incident doesn't use the words you wrote it with.
- **Retrieves the right runbook automatically** during an investigation and
  grounds the agent's finding in *your* real steps — the exact commands your team
  trusts — instead of generic advice a model invented.
- Does all of it **self-hosted**: the query is redacted before it's ever embedded,
  and you can run the embedding model inside your own network so nothing leaves
  your infrastructure.

You won't build a retrieval pipeline from scratch. We'll use
[Versus Incident](https://github.com/VersusControl/versus-incident), an
open-source incident tool whose analyze agent ships a `find_runbook` capability
that does all of this in the box. But the tool is not the point. The *idea* is
the point — keep operational knowledge open and searchable, and put retrieval
last so the expensive intelligence only ever reads what actually matters. You
could build a version of this yourself. Versus just means you don't have to.

### The thread we'll follow

The book moves in one straight line, from problem to working system:

1. **Why runbooks exist** and what a good one captures.
2. **Why they stop helping** once there are too many to find.
3. **The reframe** — knowledge to retrieve, not documents to read.
4. **The format** — an open, plain-text way to write runbooks that both a human
   and a machine can read.
5. **The retrieval** — embeddings and similarity search, explained without the math.
6. **The shortcut** — `find_runbook`, so you use a retriever instead of building one.
7. **The payoff** — a cited incident finding, backed by a real runbook.
8. **The guarantees** — privacy and accuracy, enforced, not promised.
9. **The upkeep** — keeping the knowledge base alive.

### Who this is for

You run production. You've written a runbook. And at least once, you couldn't
find it — or found it three versions out of date — at the exact moment it would
have saved you an hour. If that lands, this book is for you.

You don't need machine-learning experience. You don't need to know what an
embedding is — Chapter 5 explains it in plain terms, and Chapter 6 shows you how
to use one without ever touching the math. If you can write a Markdown file, run
a Docker container, and read a config file, you have everything you need.

Let's start with why your team writes runbooks in the first place — and what they
capture that nothing else does.
