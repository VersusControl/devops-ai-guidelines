<!-- markdownlint-disable MD041 -->

## 3. From Pages to Knowledge

Chapter 2 ended on a reframe, and it's worth saying slowly because everything else
in this book is built on it:

> Stop treating a runbook as a document a human reads later. Start treating it as
> knowledge a system retrieves now — the instant an incident fires.

Those sound similar. They lead to completely different designs. If a runbook is a
document, you optimize for humans: folders, naming, a nice wiki, a search box. If a
runbook is retrievable knowledge, you optimize for the moment of need: an open
format a machine can read, retrieval by meaning, and delivery straight into the
incident — no search box, no human remembering the right word.

That sprawl is what you get from the first design at scale. This book is the
second.

### Retrieval, not recall

The core move is to stop relying on human recall. Today, the unwritten step in
every runbook process is: *the on-call engineer must remember that a runbook
exists, and remember enough about it to search for it.* That step fails exactly
when you need it most — under stress, at 3 a.m., on a service you don't own, for a
failure you've never personally seen.

So take that step away from the human. The engineer shouldn't have to know a
runbook exists. The system should surface it — pull the right knowledge into the
incident on its own, and let the human evaluate an answer instead of hunting for
one. Recall is a human weakness under pressure. Retrieval is a machine strength.
Put the machine on the job it's good at.

### What has to be true for that to work

Retrieval-by-a-machine only works if three properties hold. The rest of the book is
just making each one real.

**1. The knowledge is in a format a machine can read.** A runbook trapped in a
proprietary wiki, behind an API, wrapped in rendering metadata, is not something you
can easily hand to a retriever. The knowledge has to live in open, plain text — a
format you own and a program can parse. That's the next chapter: the open knowledge
format.

**2. Retrieval happens by meaning, not keywords.** The incident won't use the words
your runbook used. So matching has to be semantic — "find the runbook that *means*
the same thing as this incident," not "find the runbook that shares a keyword." That
needs embeddings, and it's Chapter 5. And you don't have to build the machinery
yourself — Chapter 6.

**3. The answer arrives inside the incident.** Retrieval that dumps a link in a
search box still relies on a human to go look. The whole point is to skip that. The
right runbook should show up *in the investigation the agent is already doing*,
cited, next to the finding — so the engineer sees the fix without asking for it.
That's Chapter 7.

### The shift in who does what

Notice what this reframe does to responsibility. It doesn't ask humans to do more
— it asks them to do less of the wrong thing. People are still the authors: they
write the runbooks, capture the judgment, keep them current. That's human work, and
it stays human. What changes is that people are no longer the *index* and the
*search engine* too. They stop being the fragile part of the system — the part that
has to remember, under pressure, what exists and where.

Write the knowledge. Let the machine find it. That division of labor is the entire
design, and the next chapters build it piece by piece — starting with the shape the
knowledge has to take.
