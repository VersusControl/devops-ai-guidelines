<!-- markdownlint-disable MD041 -->

## 2. The Unknown Unknowns

There's a famous way to divide what you know. Known knowns: the things you know
you know. Known unknowns: the things you know you don't know — you know disk can
fill up, so you watch it. And then unknown unknowns: the things you don't even
know to look for.

Threshold monitoring is built entirely for the middle category. You know disk
fills, so you alert on 90%. You know latency spikes, so you alert on p99. Every
rule you've ever written is a known unknown you turned into a watched signal.

The incidents that take down production live in the third category. They're the
failures you couldn't have predicted, so you couldn't have written a rule, so
nothing was watching. This chapter is about that category — why it's the one that
hurts, and why your logs are the best place to catch it.

### What an unknown unknown actually looks like

It's rarely dramatic at first. Here are four shapes it takes, all drawn from real
postmortems:

- **A new error nobody has seen.** A library upgrade starts throwing a
  `context deadline exceeded` on one worker. It's never appeared in your logs
  before. No rule exists for it. It repeats quietly for hours.
- **A silent behavior change.** A deploy flips a config default. A feature stops
  working, but nothing errors — the code takes the wrong branch and logs a cheerful
  `200 OK` the whole time.
- **A dependency going subtly wrong.** A third-party API starts returning stale
  data. Your retries succeed, your error rate stays flat, and your users get wrong
  answers.
- **A slow drift.** A queue that normally sits at 200 messages starts creeping:
  400, then 900, then 6,000 over several hours. No single reading looks alarming.
  There's no error at all. Just a number quietly going the wrong way.

Every one of these was invisible to threshold monitoring until it was already
bad. And every one of them left a trace — usually in the logs, sometimes hours
before anyone noticed.

### Why logs are the right place to look

This book uses logs as its running example, and that's a deliberate choice. Logs
have three properties that make them the ideal signal for catching unknown
unknowns.

**Logs are where new behavior shows up first.** When something changes in your
system — a new error, a new code path, a new failure mode — it almost always
writes a log line before it moves a metric. The `context deadline exceeded` was
in the logs at 6:00 a.m. The error-rate metric didn't budge until much later, if
at all. Logs are the leading indicator; metrics are the lagging one.

**Logs are text, so "new" is obvious.** A metric is just a number going up or
down — to know if it's abnormal you need a baseline and a threshold. A log line is
a *shape*. "I have never seen this shape before" is a judgment you can make
without any threshold at all. Novelty is a first-class signal in text in a way
it simply isn't in a raw number.

**Logs repeat.** This is the property that makes the whole approach practical, and
it's easy to underestimate. A service might emit millions of lines a day, but
those lines fall into a surprisingly small number of *templates* — a few dozen
shapes account for nearly all the volume. Access logs. GC pauses. The same retry
warning. Health checks. The boring stuff is boring precisely because it happens
constantly. So when a genuinely new shape appears in that sea of repetition, it
stands out. It's a stranger in a crowd of regulars.

### The reframe: watch for *new*, not for *bad*

Put those three properties together and you get the central move of this book.

You can't enumerate every bad thing that might happen — that's the whole problem
with unknown unknowns. But you *can* learn what your logs normally look like,
because they repeat. And once you know what's normal, anything unfamiliar is worth
a look by definition.

So the model inverts. Instead of writing rules for what's *bad*, you learn what's
*normal*, and you treat anything *new* as the signal. The export failure had
never been seen before. In a "learn normal, flag new" model, that's the entire
trigger — no threshold, no rule, no prediction required. The mere fact that it was
unfamiliar was enough.

This also quietly solves the drift case. A queue creeping from 200 to 6,000 never
produces a *new* log line — but the *frequency* of an existing line can change. A
known pattern that normally fires 12 times an hour suddenly firing 1,200 times an
hour is a different kind of "new": the shape is familiar, but the rhythm isn't. We
catch that too, and Chapter 3 explains how.

### The trap you have to avoid

Here's where most "AI for logs" projects die. Someone hears "learn what's normal,
flag what's new," reaches for an LLM, pipes all the logs into it, and asks
"anything wrong here?" It works beautifully in a demo with 50 lines. In
production it fails three ways, every time:

- **Cost.** A medium service produces millions of lines a day. Sending them all to
  a model API costs more than the on-call engineer it's meant to help. The project
  gets killed when the bill arrives on day two.
- **Noise.** An LLM staring at raw logs finds "problems" everywhere. Every
  deprecation warning becomes a P1. Every successful retry becomes an incident. The
  team mutes the channel by Thursday.
- **Privacy.** Logs are full of tokens, passwords, customer emails, internal
  hostnames. Shipping them wholesale to a third party is its own security incident.

These aren't edge cases. They're the inevitable result of putting the AI at the
*front* of the pipeline, where it has to read everything. The fix — the thing that
makes "learn normal, flag new" actually work in production — is to put the
expensive intelligence at the *end*, and let cheap, deterministic code handle the
99% of logs that are boring.

That architecture is the subject of the next chapter.

**In short:**

- Unknown unknowns are the failures you couldn't predict, so no rule was watching.
  They're the ones that hurt.
- Logs are the best place to catch them: new behavior appears in logs first,
  novelty is obvious in text, and logs repeat — so "new" stands out.
- The reframe is to watch for *new*, not for *bad* — including a known line
  suddenly changing its *frequency*.
- Piping raw logs into an LLM to do this fails on cost, noise, and privacy. The
  fix is to put the AI last, not first.
