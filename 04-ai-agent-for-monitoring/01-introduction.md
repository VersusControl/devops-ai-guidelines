<!-- markdownlint-disable MD041 -->

## Introduction

Every team has the story. The dashboards were green. Every alert was quiet. And
yet something had been broken for hours — a background job failing, a queue
draining the wrong way, a new error line repeating in the logs that nobody had
ever written a rule for. You found out from a customer, or from a teammate, or
from the smoking crater the next morning.

That gap — between "something went wrong" and "you found out" — is the subject of
this book. Not because monitoring is bad. Threshold alerts are necessary and they
work. The problem is structural: **a rule can only catch what someone already
thought to watch for.** The incidents that hurt most are the ones nobody
predicted.

There's a single reframe at the center of everything here:

> Stop monitoring your *predictions* about how the system breaks. Start
> monitoring the system itself.

Instead of writing rules for what's *bad*, you learn what's *normal* — and treat
anything new as worth a look. It sounds almost too simple to work. It works
because of a quiet property of production logs: **they repeat.** A service can
emit millions of lines a day, but those lines fall into a small number of shapes.
When a genuinely new shape appears, that's information. That's the whole trigger.
No threshold. No rule. The mere fact that it's unfamiliar is the signal.

This is not a new idea. Spam filters, fraud detection, and intrusion detection
have modeled a baseline and flagged the deviation for decades. What's newer is
pointing that approach at your application logs and wiring the output into the
incident pipeline your team already trusts.

### What you'll build

By the end of this book you'll have a working system that:

- Reads your logs continuously and learns what's normal — without you writing a
  single rule.
- Tells you what it *would* have alerted on, before it alerts on anything.
- When you trust it, asks an AI to triage the survivors and routes the result
  through the Slack, Teams, or PagerDuty channels you already use.

The AI sees less than 1% of your logs. The other 99% never leave your
infrastructure. Cost is bounded by a hard cap. Privacy is bounded by redaction
that runs first. Noise is bounded by a baseline you trained yourself.

We'll use [Versus Incident](https://github.com/VersusControl/versus-incident), an
open-source incident tool that ships this agent in the box, as the concrete
implementation. But the tool is not the point. The *idea* is the point — learn
the baseline, flag the deviation, put the expensive intelligence last. You could
build a version of this yourself in any stack. Versus just means you don't have
to.

### Who this is for

You run production. You've been paged at 3 a.m. You've written the postmortem
sentence "the signal was there, we just weren't watching it." You've muted a
Slack channel to survive an on-call week. If any of that lands, this book is for
you.

You don't need machine-learning experience. You don't need to know what an
embedding is. If you can read a config file, run a Docker container, and tail a
log, you have everything you need.

Let's start with why the monitoring you already have will always be a little
late.
