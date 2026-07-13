<!-- markdownlint-disable MD041 -->

## 8. Operating It, Honestly

"AI watches your logs" is the kind of sentence that invites overselling. This
closing chapter is the honest debrief — what the agent replaces, what it doesn't,
the mistakes that bite, and how to keep it healthy after the novelty wears off.

### What this does and doesn't replace

**It does not replace your threshold alerts.** If you have a good rule for high
error rate or p99 latency, keep it — it will often fire *faster* than log analysis
for the failures it was built for. Anomaly-first detection is a complement, not a
replacement. It catches the things your rules can't, which is a different job than
catching the things your rules can. The two together cover far more than either
alone.

**It only sees what's in your logs.** If a failure produces no log line — silent
data corruption, a metric-only regression — log analysis won't catch it. This is
why the longer-term direction is metrics and traces too, not just logs. Logs are
the first signal, not the only one.

**It depends entirely on the quality of your training period.** A baseline learned
during a quiet week will flag normal Monday traffic as anomalous. You have to
train across a real cycle — the deploys, the batch jobs, the Thursday cron that
always looks weird. Shadow mode exists precisely so you discover those before they
page you.

### The mistakes that bite

A handful of traps come up again and again. Worth saving you the trip:

- **Skipping training.** "Two hours should be enough." It isn't. The catalog needs
  to see your nightly batches, your weekly cron, your deploy noise. A day minimum,
  ideally a full release cycle.
- **Filter rules that are too loose.** `default_pattern: ".*"` is right for
  training. In detect, if you leave it that broad and never label patterns, every
  rare line becomes an AI call. Tighten it, or label aggressively.
- **No new-service grace.** The first time you deploy a new service after going
  live, every line from it is `unknown` by definition. Set `new_service_grace` to
  at least 30 minutes so the agent doesn't page on a service's first breath.
- **Trusting the AI's severity blindly.** The model is calibrated to be
  conservative, but it's still a model. Review the first week of incidents and
  surface the confidence score in your channel template — anything below ~0.7
  deserves a human glance before it pages.
- **Forgetting to rotate keys that appeared in logs.** Redaction scrubs the common
  shapes (`sk-…`, `xoxb-…`, AWS keys, JWTs, basic-auth URLs), but treat it as
  defense-in-depth, not a guarantee. If a secret ever made it into a line you fed
  the agent, rotate it.

### A big deploy can blind the filter — plan for it

There's one failure mode you should know before you ship. If a release changes
your log formats wholesale, every new line looks `unknown` until the baseline
relearns. Suppression drops, AI calls climb toward the cap, and — worse — real
problems can hide in the flood of newly-unfamiliar-but-benign lines.

The fix is operational, not configurable: retrain the baseline after major logging
changes, and watch your suppression-rate metric so you *notice* the day it happens
instead of finding out from the invoice. The rate cap protects your wallet during
that window; it doesn't protect your signal. That's a tradeoff, not a bug you can
config away.

### Measure the right things

Stop measuring cost per log line — it's the wrong denominator, and it makes a
chatty service look expensive when nothing is wrong. Watch three numbers instead:

- **Suppression rate** — the fraction of events that never reached the model. You
  want this in the high 90s. If it drops, your baseline needs retraining (usually
  after a deploy that changed a log format).
- **Model calls per hour** — should sit well under your cap in steady state.
  Pinned at the cap means something upstream is misclassifying — a bug to fix, not
  a bill to pay.
- **Cost per real incident** — the number that actually reflects value. When
  suppression and call-rate are healthy, this is boring and predictable, which is
  exactly what you want a bill to be.

The agent also exposes its own health: signals per tick, the verdict distribution
(known vs. unknown vs. spike), cache hit rate, catalog size, tick duration. You
monitor the monitor. When the unknown ratio spikes and stays high, the catalog
needs attention — often the sign of a new logging format after a deploy.

### The honest state of the art

Where does this class of tooling really sit in 2026? Think of a capability ladder:
detect → investigate → correlate → recall → act.

- **Detect and investigate** are here and real: learning normal, flagging new,
  triaging with an AI that explains itself and cites context.
- **Recall** — grounding the AI in your own runbooks so it cites your team's
  remediation steps instead of guessing — is available and worth turning on.
- **Correlate** across logs, metrics, and traces into a single incident is
  emerging.
- **Act** — an agent that proposes *and applies* a fix autonomously — is mostly not
  here yet, and anyone claiming otherwise is selling a demo. Autonomy needs
  self-hosting and airtight audit trails before it belongs anywhere near
  production, and that bar is high for good reason.

Be skeptical of any vendor whose "autonomous" turns out to be a smarter alert with
a chatbot bolted on. The honest version of this technology is powerful precisely
because it's modest: it watches for *new*, explains what it found, and hands a
human a head start. That's not a small thing. It's the difference between a
four-hour silent outage and a five-minute page.

### The path forward

If you take one idea from this book, let it be the reframe: **stop monitoring your
predictions, start monitoring your system.** Threshold rules encode what you
already know can break. They're necessary and they're not enough. The failures
that hurt are the ones you didn't predict, and the only way to catch those is to
watch for *new*, not for *bad*.

You don't need anyone's tool to apply that principle — it works in anything you
build. But if you'd rather not write the plumbing from scratch, point the agent at
a log file, leave it in training for a few days, and see what it learns about your
system. It'll probably surface something you stopped seeing a long time ago.

---

## Additional Resources

- **[Versus Incident](https://github.com/VersusControl/versus-incident)** — the open-source incident tool with the SRE agent built in.
- **[Agent documentation](https://docs.versusincident.com)** — the miner, catalog, spike detection, redaction, and
  the three modes, each with full configuration.

The whole thing is Apache-2.0. Fork it, run it on staging for a week, and see what
it catches.

**In short:**

- The agent complements threshold alerts; it doesn't replace them, and it only
  sees what's in your logs.
- The common mistakes are all operational: under-training, loose filters, no
  new-service grace, blind trust in severity, unrotated leaked keys.
- A big deploy can blind the filter — retrain after logging changes and watch your
  suppression rate.
- Measure suppression rate, calls per hour, and cost per incident — not cost per
  log line.
- "Detect and investigate" are real today; "act" is not. The honest value is a
  human head start, and that's enough.
