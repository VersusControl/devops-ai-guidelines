<!-- markdownlint-disable MD041 -->

## 6. The Logs Page: Watching It Learn

A catalog scrolling past in a terminal is hard to reason about. The admin UI is
where the agent stops being an abstraction and becomes something you can watch,
sort, and correct. This chapter is a guided tour of the pages you'll actually live
in while the agent is learning.

Versus serves the admin UI on the same port as the agent. Open
`http://localhost:3000` and sign in. The left rail is organized by *job*, not by
backend module, into five zones:

- **Respond** — Now, Incidents.
- **Agent** — Overview, Services, **Logs**, Metrics, Traces. The calm-curation
  zone, and where this chapter lives. (Metrics and Traces are Enterprise; on the
  open-source build they show a lock.)
- **AI** — Decisions, Analyses, SLIs/SLOs. The agent's reasoning surfaces —
  Chapter 7's territory.
- **Tools** — Runbooks.
- **Manage** — People, Admin, Settings.

> **Note:** If the agent is off (`agent.enable: false`), the entire Agent zone is
> dimmed and locked with the hint *"AI agent is disabled — set agent.enable to use
> these views."* If that's what you see, go back to Chapter 5.

### Agent → Overview: the runtime at a glance

The **Overview** page (the Agent zone's landing page, titled simply "Agent")
answers one question fast: *is the agent on, what mode is it in, and what has it
been doing?*

At the top sits the **runtime banner**. It shows three things, each as a labeled
chip so state is never conveyed by color alone:

- **Agent** — an `enabled` or `disabled` pill.
- **Mode** — a chip with an icon: *Training* (a graduation cap), *Shadow* (an
  eye-off), or *Detect* (a radar). This is the single most important thing on the
  page — it tells you what the agent is *allowed* to do right now.
- **AI SRE** — a pill showing the model name (e.g. `gpt-4o-mini`) when AI is on,
  or `off`.

Below the banner, a row of **Lifetime totals** tiles gives you the shape of the
agent's work: *Services tracked*, *Shadow events*, *Detect events*, *Log
patterns*, *Incidents emitted*, *AI cache hits*, *AI / send errors*, and *Total
signals*. Each tile is a link into the page behind it, so the *Log patterns* tile
clicks straight through to the Logs page.

Two cards make recent activity concrete — **Top patterns by sightings** (your
noisiest templates, with their normal rate and verdict) and **Recent shadow
events** — and a set of **breakdown** cards tally the rest: *Verdict breakdown
(shadow)*, *Detect outcomes*, *Detect verdicts*, and *AI severity*. During training
you'll mostly glance at the banner to confirm the mode, then head to the Logs
page.

### Agent → Logs: the catalog, made visible

This is the page the whole chapter is named for, and the one you'll return to
forever. Its header says it plainly: **"What the agent knows right now"**, with a
subtitle counting how many log templates it has learned. A one-line description
sits under it — *"The recurring log messages the agent has learned for each
service, and how often each normally shows up."*

Each learned template is a row, most-frequent first. The columns are deliberately
few, and every header carries a small **info hint** you can hover for a
plain-English explanation:

| Column | What it tells you |
|---|---|
| **Service** | The service the line was attributed to (from service detection). |
| **Template** | The learned shape, with `<*>` marking the parts that change from line to line. |
| **Count** | Lifetime total — how many raw lines have matched this template since learning began. |
| **Normal** | The learned rate, shown as `≈ 1.3/s`. This is the EWMA baseline the spike detector compares against. |
| **Verdict** | The agent's current label for the template (see below). |

The **Verdict** cell is where "learning" becomes visible. A freshly-mined template
shows **Still learning** with a small progress bar and a `seen / needed` count —
for example `40 / 100`. That's the readiness gauge from Chapter 3 made literal:
the agent wants to see this template around 100 times before it auto-promotes it
to **Known**. Once promoted (or once you label it), the cell reads **Known** and
the template stops surfacing as new. A template that recently surged past its
baseline reads **Spike**.

Three controls sit above the table:

- A **filter** — *All* / *Still learning* / *Known*, each with a live count. During
  training, watching the *Still learning* count fall and the *Known* count rise
  **is** watching the agent learn. When *Still learning* stops shrinking, your
  baseline is stabilizing.
- A **search** box — match on template, service, id, or rule. (Press `/` to jump
  to it.)
- An **auto-refresh** toggle, so the table updates itself as new logs flow in.

> **Tip:** Filter to *Still learning* and let it auto-refresh — new rows appear as
> the miner picks up unfamiliar shapes. Filter to *All* and the highest-**Count**
> rows at the top are the boring stuff drowning out your signal: health checks,
> access logs, retries that always succeed. That's exactly the noise the agent
> will silence for you.

### Inspecting one pattern: the peek panel

Click the **eye** icon on any row (or press `Enter` with the row focused) and a
**peek panel** slides in from the right — inspect without losing your place in the
list. It shows:

- The **verdict** and the **rule** that matched the line.
- The full **template**.
- A facts grid: **Count**, **To known** (the readiness progress), **First seen**,
  **Last seen**, **Service**, **Rule**, **Source**, and **Tags**.
- A **What's normal** section rendering the learned baselines — the frequency, its
  spread, and the per-hour (seasonal) view behind the spike detector.
- An **Example log line** — the most recent real line that matched.

A footer link, **Open full page ↗**, takes you to the pattern's own page for
editing.

### Curating from the list

You don't have to open each pattern to label it. Select one or more rows with
their checkboxes and an **action bar** appears with the curation actions:

- **Mark known** — silence a template. Use it for benign noise: nightly batch
  output, an acknowledged deprecation warning, intentional debug lines. Each one is
  a false alert you won't get later.
- **Clear verdict** — send a template back to *Still learning*.
- **Assign to service** — fix a mis-attributed service on the pattern.
- **Ignore / Resume** — hold a noisy pattern out of learning entirely (an
  Enterprise control; it adds an *Active | Ignored* scope switch above the table).

There are keyboard shortcuts for the same moves: `j` / `k` to move between rows,
`Enter` to open, and `K` to mark the focused row known. Every action lands a toast
with an **Undo**, so a mis-click is one click to reverse.

### The pattern detail page

**Open full page ↗** (or a row's `/agent/logs/<id>` link) opens the full editor
for a single template. Here you can:

- Set the **verdict** directly — *(none)* / *known* / *spike* — from a dropdown.
- Edit **tags** (comma-separated) for your own grouping.
- **Save** the changes, or **Delete** the pattern outright.
- **Reassign** the detected service, when regex service-detection guessed wrong.

The page also renders the full baselines and readiness, so it doubles as the
deepest view of what "normal" means for that one shape.

> **Tip:** Prefer **Mark known** over **Delete**. A deleted pattern is simply
> re-learned the next time it appears; a *known* pattern is remembered and stays
> quiet.

### The reset switch

The Logs header carries one destructive action: **Clear all logs**. It wipes every
learned template, resets the miner, and starts the baseline over from scratch — the
right move when the catalog has learned garbage from a bad source or a test flood,
and the wrong move any other time. It asks for confirmation, and it can't be
undone. Reach for single-pattern **Delete** first; keep **Clear all logs** for a
genuine "start over."

### Agent → Services

One page over, **Services** lists everything the agent discovered from your log
lines, and whether each is still inside its *new-service grace* window (learning,
not yet alerting) or fully *tracked*. It's where you confirm the agent is
attributing lines to the right service before you trust its per-service behavior in
detect mode — which is exactly where the next chapter picks up.

**In short:**

- The UI's left rail is organized by job into Respond / Agent / AI / Tools /
  Manage; the learning views live under **Agent**.
- **Overview** shows the runtime banner (enabled + mode chip + AI SRE model) and
  lifetime activity — glance here to confirm the mode.
- **Logs** is the catalog made visible: Service, Template, Count, Normal, Verdict.
  The *Still learning → Known* progress is the agent learning in real time.
- Inspect with the **peek panel**; curate with **Mark known / Clear verdict /
  Assign / Ignore** from the selection bar, or the full **pattern detail** page.
- **Clear all logs** is the only destructive reset — confirmed and un-undoable.
