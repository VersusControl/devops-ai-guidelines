<!-- markdownlint-disable MD041 -->

## 1. The Problem With Old Monitoring

An export worker started failing at 6 a.m. It threw `context deadline exceeded`
on every job. Thousands of exports failed over the next four hours. Not one alert
fired.

The dashboards were green the whole time. CPU normal. Memory normal. Error rate
flat at 0.2%. Every threshold quiet. The failure only surfaced at 10 a.m., when a
customer sent a Slack message: *"Hey, exports have been failing since this
morning?"*

That's the day a lot of engineers stop trusting their alerts to catch
everything. Not because the alerts were badly configured — they were fine. The
problem is deeper than configuration. It's structural. And once you see it, you
can't unsee it.

### Alerts encode what you already fear

Threshold monitoring runs on a simple model. You predict a failure, you write a
rule, the rule catches it.

- CPU over 80%.
- Error rate over 1%.
- Disk over 90%.
- p99 latency over 500ms.

Every one of those is a *prediction* you made in advance about how your system
would break. This is great for the failures you can imagine. It does nothing for
the ones you can't.

The export worker's `context deadline exceeded` never tripped a threshold. Error
rate stayed at 0.2% because the failing job was a small slice of total traffic.
CPU and memory were fine because a stuck worker isn't a busy one. There was no
rule for that error on that worker, because nobody had ever thought to write one.
Why would they? You can't write a rule for a failure you've never seen.

This is the quiet truth about threshold monitoring: **you're not monitoring your
system. You're monitoring your predictions about your system.** The gap between
the two is exactly where incidents live.

### Why alerts are always a little late

When an alert fires late, the instinct is to blame the config. Bump the
threshold. Shorten the window. Add another rule. But late alerts usually aren't a
tuning problem. They're a timing problem — and there are three separate delays
stacked on top of each other.

**Detection lag** — the time between the problem starting and your monitoring
noticing. A threshold alert that evaluates every 60 seconds and requires 5
minutes of sustained breach has at least 5 minutes of built-in detection lag.
That's by design; it's how you avoid flapping on every blip. But it's still lag.

**Notification lag** — the time between detection and the alert reaching a human.
Usually small, unless your routing batches or deduplicates.

**Response lag** — the time between the human seeing the alert and doing
something. Runbooks and practice help here.

Most teams pour their energy into the last two. Faster paging. Better runbooks.
Fewer noisy channels. Almost nobody looks at detection lag, because it feels
fixed — a law of physics you have to live with.

It isn't fixed. Detection lag has a floor you can't tune away:

> You cannot detect what you never wrote a rule for.

For the export failure, detection lag wasn't 5 minutes. It was four hours, and it
only ended because a customer did the monitoring for us. No amount of threshold
tuning would have changed that. There was nothing to tune. There was no rule.

### "Just add another rule" doesn't scale

The natural response to a missed incident is to add a rule for it. And you
should — after an outage, encoding "never let this specific thing happen silently
again" is good hygiene.

But this strategy has a ceiling, and you hit it fast. Every rule you add is one
more thing to maintain, tune, and eventually mute when it gets noisy. More
importantly, each rule only ever covers *one* failure mode you already know
about. The space of failures you *don't* know about is effectively infinite. You
can add rules for a lifetime and never close the gap, because the gap isn't made
of the failures you've seen. It's made of the ones you haven't.

Think about your last handful of real incidents. Be honest about how you found
out:

- A dependency started returning subtly wrong data — no errors, just bad answers.
- A deploy changed a config default and a feature silently stopped working.
- A third-party API began rate-limiting you, and your retry logic absorbed it
  until it didn't.
- A slow memory leak that took six days to matter — far outside any alert window.

None of these trip a threshold until it's already bad. By the time error rate
climbs past 1%, the damage is done. And in almost every case, the signal was
sitting in the logs the whole time — a new error line, repeating — while no rule
watched for it.

### Where this chapter leaves us

Threshold monitoring is not the villain of this book. Keep your alerts. A good
rule for high error rate or p99 latency will often fire *faster* than anything
else for the failures it was designed for. This is not a replacement pitch.

But be clear-eyed about the limit. Rules catch the failures you predicted. They
are necessary, and they are not enough. The failures that hurt — the four-hour
export outage, the silently broken feature, the leak that took a week — are the
ones you didn't predict. And the only way to catch a failure you didn't predict
is to stop looking for *bad* and start looking for *new*.

That class of failure has a name. It's the subject of the next chapter.

**In short:**

- Threshold alerts can only catch failures someone predicted in advance.
- Every alert carries three delays; teams tune the last two and ignore detection
  lag — which has a floor you can't tune away.
- "Add another rule" covers one known failure at a time and never closes the gap.
- The fix isn't a better rule. It's a different question: not "what's bad?" but
  "what's new?"
