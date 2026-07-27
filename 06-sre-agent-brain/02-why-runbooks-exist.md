<!-- markdownlint-disable MD041 -->

## 1. Why Runbooks Exist

Start with a good one. It's 12 p.m., checkout is throwing errors, and instead of
waking the one engineer who understands the payment path, you open a file. It
tells you the symptom to confirm, the two commands that diagnose it, the fix, and
when to roll back instead. You run the steps. The page clears. You go back to bed.
Nobody had to be a hero.

That file is a runbook, and it exists for one reason: **incidents repeat, and
nobody wants to re-derive the fix under pressure.** The first time a failure
happens, someone figures it out the hard way — reading code, tailing logs,
guessing. That's expensive, and it's slow, and it happens at the worst possible
time. A runbook is the receipt for that work. Write it down once, and the second
time the failure happens it costs minutes instead of hours.

### What a runbook captures that nothing else does

Your dashboards and alerts tell you *something is wrong*. A metric crossed a line;
an error rate climbed. That's detection. It is not the same as knowing what to
*do*. A runbook lives on the other side of that gap. It captures the part that
isn't in any graph:

- **The symptom, in plain words** — what this failure actually looks like, so you
  can confirm you're in the right place. "Postgres refuses new connections and the
  api logs `remaining connection slots are reserved`."
- **The diagnosis** — the specific checks that tell you what's really happening,
  not what merely looks true. "Count active connections; look for idle-in-transaction
  sessions."
- **The remediation** — the exact steps, with the real commands. Not "restart the
  service" but the command, the flag, the order.
- **The decision points** — when to do the safe thing versus the drastic thing.
  "If the leak is app-side, roll back the last deploy instead of killing sessions."
- **The escalation** — who to call, and when it's no longer safe to keep trying.

None of that is in a metric. All of it is judgment — the accumulated experience of
the people who fixed this before you. A runbook is how that judgment survives past
the person who had it.

### The value is institutional, not personal

The quiet reason runbooks matter is that they turn a hero-dependent response into a
repeatable one. Without them, incident response scales with the number of people
who happen to remember the fix — and that number goes to zero the day someone
takes a vacation, changes teams, or leaves. A team that writes runbooks is a team
whose knowledge doesn't walk out the door.

They also shrink the two numbers that matter most on-call:

- **Mean time to recovery** drops, because the fix is looked up instead of
  rediscovered.
- **The blast radius of inexperience** drops, because a junior engineer with a good
  runbook can resolve an incident that used to require the senior who wrote it.

This is real, durable value, and it's why every serious on-call team eventually
writes runbooks. The investment is sound.

### The catch

Here's the whole tension this book is about. The value of a runbook is entirely
contingent on one thing: **you can find the right one, fast, at the moment you
need it.** A runbook you can't locate at 3 a.m. delivers none of the value above.
The fix is written down and you're still rediscovering it from scratch — now with
the extra frustration of knowing it exists.

For one runbook, or ten, finding it is trivial. For a hundred, spread across a wiki
and three repos and someone's bookmarks, it stops being trivial. It becomes the
problem. That's where we go next.
