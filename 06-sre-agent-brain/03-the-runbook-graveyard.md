<!-- markdownlint-disable MD041 -->

## 2. When Runbooks Don't Scale

The trouble doesn't start when you have too few runbooks. It starts when you
succeed. You write them carefully, for two years, across a growing team — and one
day you have four hundred of them, and the pager goes off, and you cannot find the
one you need.

This is runbook sprawl: a large, valuable pile of written knowledge that
has quietly become unusable. Not because any single runbook is bad, but because the
*collection* crossed a threshold where the humans can no longer hold it in their
heads or search it under pressure.

### Where they scatter

Runbooks rarely live in one place. Over time they scatter:

- Some in the team **wiki** — Confluence, Notion, an internal portal.
- Some in **git repos**, next to the code, as `README` sections or `docs/`.
- Some in **Google Docs** a manager made during a postmortem.
- Some in **Slack threads** — the real fix, buried in a reply, never written up.
- Some only in **someone's head**, never written at all.

No single search covers all of those. So finding the right runbook means
remembering *which* place it's in before you can even look — a second guessing game
on top of the incident.

### The three ways they fail you

**They're unfindable by keyword.** This is the deep one. You search your wiki for
the words in the alert — `remaining connection slots reserved` — and get nothing,
because the person who wrote the runbook titled it "Postgres connection pool
exhausted" and never pasted the raw error. The knowledge is *right there*. The
words just don't match. Keyword search only finds runbooks written in the same
vocabulary as the incident, and incidents don't read your runbooks first.

**They go stale silently.** A runbook is a snapshot of how the system worked when
someone wrote it. The command changes. The service gets renamed. The rollback
procedure is now two steps instead of one. Nobody updates the doc, because nobody
had an incident that used it — until tonight, when you follow it faithfully and it
makes things *worse*. A stale runbook is more dangerous than no runbook, because it
carries the authority of a written procedure while pointing you off a cliff.

**They duplicate and contradict.** Three people wrote a runbook for the same
failure, in three places, over three years. None is marked authoritative. Now
finding the runbook isn't enough — you have to find the *right* one, and reconcile
the ones that disagree, in the middle of an outage.

### Why "reorganize the wiki" never fixes it

The instinct is always the same: the runbooks are a mess, so impose order. A new
folder structure. A naming convention. A quarterly cleanup. It feels productive,
and it never lasts, because it misattributes the problem. **This isn't an
organization problem. It's a retrieval problem.**

Organization assumes a human will navigate a hierarchy to find a document. But at
3 a.m., mid-incident, the human doesn't want to navigate — they want the answer.
No folder structure survives contact with a pager, because the whole failure mode
is that the person under pressure doesn't know the exact term, the exact folder, or
even that a runbook exists at all. You can reorganize the pile into tidy
folders. It's still unsearchable.

### The real cost

Add it up and the cost is precise: **your MTTR on *known* incidents stops
improving, and then gets worse.** The failures you've seen before — the ones a
runbook should make cheap — start taking as long as novel ones, because the lookup
tax eats the savings. The investment you made writing all those runbooks stops
paying off. You have the knowledge and you can't spend it.

The fix is not more runbooks and not more organizing. It's changing what "finding a
runbook" even means — from a human remembering the right search term, to a system
that retrieves the right knowledge by meaning, automatically, the instant the
incident fires. That reframe is the next chapter.
