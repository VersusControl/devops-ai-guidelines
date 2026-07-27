<!-- markdownlint-disable MD041 -->

## 9. Operating Your Knowledge Base

A knowledge base is not a project you finish. It's a thing you keep alive. The
retriever from Chapter 6 is only ever as good as the runbooks you feed it — and
runbooks, left alone, drift toward the sprawl of Chapter 2. This last chapter is
the day-two work that keeps that from happening. The good news: it's light, and most
of it is habits, not tooling.

### Adding and updating runbooks

Two ways in, and you'll use both:

- **Drop a file.** Add or edit a Markdown file in your `runbooks/` folder, commit
  it, and on the next boot the server ingests it. Ingestion is **incremental**: only
  new or changed files are re-embedded, so an edit costs one embedding call, not a
  full rebuild — and a restart with no edits costs nothing.
- **Use the admin UI.** From the Runbooks page you can upload, view, and delete
  runbooks without a restart. An upload rebuilds the search index atomically, so the
  new runbook is searchable the moment it lands. This is the fast path for a fix you
  just discovered mid-incident and want available *now*.

Pick whichever fits the moment. The file-in-git path is better for durable, reviewed
knowledge; the UI is better for capturing something urgently.

### Scope as you grow

The single habit that keeps retrieval sharp as the corpus grows is setting the
`service` (or `services`) front-matter, as covered in Chapter 4. Ten runbooks don't
need it. Four hundred do — it's what lets a search scope to the service that's
actually on fire and stops unrelated runbooks from crowding the results. Make it part
of your runbook template so it's never an afterthought.

### Pre-baking for CI and air-gapped builds

You usually don't need this — the server ingests at boot. But if you build images in
CI, or ship into an air-gapped environment, you may want the corpus already
populated when the container starts. A `runbook-ingest` command builds it
out-of-band: it reads the same `runbooks/` directory, the same embedding model, and
the same key the server uses, and produces a corpus the server loads on startup with
zero ingestion calls. Bake it into your image build and the agent starts fully armed.

### Treat runbooks like code

The failure mode that undoes everything is the stale runbook — the one that carries
the authority of a written procedure while pointing at a command that no longer
exists. A stale runbook is worse than a missing one, because now the *agent* cites
it, lending it even more credibility. The defense is the same one you already use for
code:

- **Review runbook changes in pull requests.** Because they're plain files in git
  (Chapter 4), a runbook edit is a diff a teammate can review. Knowledge that goes
  through review stays current; knowledge in a wiki nobody opens goes stale.
- **Update the runbook when the fix changes.** When a remediation changes — a new
  command, a renamed service, a different rollback — the runbook edit is part of the
  change, not a someday task.

### Close the loop with your incidents

Your incidents tell you exactly what to write and what to fix. Two signals, both
free:

- **A `found: false` from `find_runbook`** (Chapter 7) is a to-do list. It means a
  real incident had no matching runbook. If that failure is worth being able to fix
  fast next time, write the runbook. The gaps announce themselves.
- **The Tool calls trail** shows which runbooks are actually matching real incidents.
  The ones that never match are candidates to sharpen (vague body, missing error
  strings) or retire. The ones that match often are your most valuable knowledge —
  keep them impeccably current.

This is the loop that makes the knowledge base compound: incident fires → was there a
runbook? → if not, write one; if it was stale, fix it. Do that, and every incident
leaves the system a little smarter than it found it. The sprawl runs in reverse.

### Where you've landed

You started with a pile of runbooks that were valuable and unusable. You finish with
a knowledge base that's open (you own the files), searchable by meaning (embeddings,
not keywords), retrieved automatically (the agent, not a human's memory), private
(redacted, self-hostable), and verifiable (read-only and audited). You wrote the
knowledge once; now it shows up, cited, the moment it's needed — and it gets better
every time the pager goes off.

Your team already wrote the fix. Now the fix can find *you*.

---

## Additional Resources

- **Versus Incident (source & docs)** —
  [github.com/VersusControl/versus-incident](https://github.com/VersusControl/versus-incident)
  · [docs.versusincident.com](https://docs.versusincident.com)
- **`find_runbook` guide** —
  [docs.versusincident.com/#/agent/analyze-tools/find-runbook](https://docs.versusincident.com/#/agent/analyze-tools/find-runbook)
- **Analyze tools overview** —
  [docs.versusincident.com/#/agent/analyze-tools/overview](https://docs.versusincident.com/#/agent/analyze-tools/overview)
- **The Versus SRE Agent** (companion book — learn-normal / flag-new detection) —
  the book this one builds on.
