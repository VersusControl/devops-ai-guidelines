<!-- Cover -->

<h1 align="center" style="border-bottom: none">
  <img alt="The Versus SRE Agent" src="https://cdn.jsdelivr.net/gh/VersusControl/devops-ai-guidelines@main/06-sre-agent-brain/images/runbook-brain-book-cover.svg" style="max-width: 300px">
</h1>

<div align="center">

If you like the book version, check here to download: [The SRE Agent Brain](https://drive.google.com/file/d/19DG8mtCwFGSSqadMR6v99FN-0EZeULuu/view?usp=sharing)

# The SRE Agent's Runbook Brain

### Building System Knowledge for Your SRE Agent

*Your team already wrote the fix. Teach your agent to find it — the moment the incident fires.*

</div>

---

<!-- Table of Contents -->

## Contents

**0. [Introduction](#introduction)** — The fix was already written. Nobody could
find it in time.

**1. [Why Runbooks Exist](#1-why-runbooks-exist)**
What a runbook actually is, why every team on-call eventually writes them, and
what a good one captures that a dashboard never will.

**2. [When Runbooks Don't Scale](#2-when-runbooks-dont-scale)**
What happens once you have hundreds: scattered across wikis, repos, and Slack
threads, quietly going stale, and impossible to find at 3 a.m. — the moment you
need them.

**3. [From Pages to Knowledge](#3-from-pages-to-knowledge)**
The reframe: a runbook isn't a document you read later, it's knowledge you
retrieve now. What has to change for that to be true.

**4. [Open Knowledge Format](#4-open-knowledge-format)**
Writing runbooks as open, plain-text, portable knowledge — Markdown plus a
little structured metadata. Human-readable and machine-readable at the same time,
owned by you, not locked in a SaaS wiki.

**5. [How Retrieval Works](#5-how-retrieval-works)**
Embeddings and similarity search in plain terms. Why "find the runbook that
*means* this incident" beats "grep for a keyword" — no ML background required.

**6. [Don't Build Your Own](#6-dont-build-the-retriever--use-find_runbook)**
Versus Incident ships the whole retrieval pipeline. Point it at your runbooks and
skip building your own RAG stack — configure the embedding model, drop your files
in the corpus, done.

**7. [Using Runbooks in a Live Incident](#7-using-runbooks-in-a-live-incident)**
How the agent pulls the right runbook mid-incident and cites *your* real
remediation steps instead of inventing generic advice — read-only, and recorded
in the audit trail.

**8. [Keeping It Private and Verifiable](#8-keeping-it-private-and-verifiable)**
Redaction before embedding, self-hosted embeddings, and why your operational
knowledge never leaves your infrastructure.

**9. [Operating Your Knowledge Base](#9-operating-your-knowledge-base)**
Ingesting and updating runbooks, scoping by service, pre-baking the corpus for CI
or air-gapped builds, and keeping it fresh so the agent never cites a stale fix.

**[Additional Resources](#additional-resources)**

---
