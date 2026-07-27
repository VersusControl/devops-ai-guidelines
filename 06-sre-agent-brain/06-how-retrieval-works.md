<!-- markdownlint-disable MD041 -->

## 5. How Retrieval Works

You have your runbooks in an open format now (Chapter 4). This chapter is about the
one piece of machinery that makes them findable by meaning instead of by keyword.
It has a slightly intimidating name — *embeddings* — and it is genuinely simple once
you see what it's for. We'll build the intuition first, then watch the whole
pipeline run over the exact three-runbook bundle from Chapter 4, in about twenty
lines of code. No heavy math, no ML background. Promise.

### The problem, one more time, precisely

An incident fires and the api logs `FATAL: remaining connection slots are reserved`.
Your runbook for exactly this is titled "Postgres connection pool exhausted," and
its body talks about `pg_stat_activity` and idle sessions. A human who reads both
instantly knows they're the same thing. A keyword search does not — the two texts
barely share a word. "Connection slots reserved" and "pool exhausted" mean the same
thing and *look* completely different.

Keyword search matches strings. What you need is something that matches *meaning*.

### Embeddings, in plain terms

An **embedding** is a way to turn a piece of text into a list of numbers — a point
in space — such that texts that *mean* similar things land near each other, even
when they use different words.

Picture a giant map. Every runbook gets a location on it, placed by meaning: all the
database-connection runbooks cluster in one region, the TLS-certificate runbooks in
another, the out-of-memory runbooks in a third. The map doesn't care about
vocabulary. "Connection pool exhausted" and "remaining connection slots reserved"
land in nearly the same spot, because they mean nearly the same thing.

That's the whole trick. An embedding model — a piece of software that already
understands language — reads a text and hands back its coordinates on that map. You
don't train it, you don't tune it; you call it, the way you'd call any API.

### Similarity search

Once every runbook has a location, retrieval is easy to describe:

1. Take the incident text and get *its* coordinates from the same model.
2. Find the runbooks closest to that point on the map.
3. Return the nearest few.

That's a **similarity search**. "Nearest few" is usually called **top-K** — the K
closest matches, ranked. Each match comes with a **similarity score** (higher =
closer in meaning), so you can tell a strong match from a weak one.

Because the map is built from meaning, this finds the Postgres runbook for our
incident even though the two texts don't share the keyword. You searched for what
the incident *means*, and the right runbook was sitting right next to it.

### Under the hood, in code

It's worth seeing the whole thing at once, because it's smaller than you'd guess.
Retrieval has two phases: an **ingest** phase that embeds every runbook once, and a
**query** phase that embeds the incident and compares. Here's ingest — read each
OKF file, split off the frontmatter, and embed the text:

```python
import os, glob, yaml, numpy as np
from embedder import embed   # any model: a self-hosted ollama, gemini, openai…

def load_okf(path):
    raw = open(path).read()
    _, frontmatter, body = raw.split("---", 2)   # OKF: --- yaml --- then body
    meta = yaml.safe_load(frontmatter)
    return meta, body.strip()

# Embed the whole bundle once. Each vector is just a list of numbers —
# a point on the "map" from earlier in the chapter.
corpus = []
for path in glob.glob("data/runbooks/*.md"):
    meta, body = load_okf(path)
    text = " ".join([meta.get("title", ""), *meta.get("tags", []), body])
    corpus.append({
        "id": os.path.basename(path),
        "service": meta.get("service"),
        "vector": embed(text),               # e.g. 768 floats
    })
```

Notice how little the frontmatter has to do: `service` becomes a filter, `title`
and `tags` fold into the text so the model sees them, and the body carries the real
signal. That's the whole reason Chapter 4 pushed concrete bodies — the error strings
and commands are exactly what the embedding captures.

Now the query phase. Embed the incident with the *same* model (same map), keep only
the runbooks for the service that's on fire, and rank by closeness:

```python
def cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

def find_runbook(query, service=None, k=3):
    q = embed(query)                                   # same model as ingest
    hits = [c for c in corpus if service in (None, c["service"])]
    ranked = sorted(hits, key=lambda c: cosine(q, c["vector"]), reverse=True)
    return [(c["id"], round(cosine(q, c["vector"]), 2)) for c in ranked[:k]]
```

`cosine` is the "how close are these two points" measure — `1.0` is the same
direction, `0.0` is unrelated. That's the entire ranking function. Run it on our
incident:

```python
>>> find_runbook(
...     "FATAL: remaining connection slots are reserved, api pool exhausted",
...     service="api",
... )
[('postgres-pool-exhausted.md', 0.89),
 ('api-5xx-spike.md',           0.42),
 ('redis-oom.md',               0.31)]
```

The Postgres runbook wins at `0.89` even though the incident says "connection slots
reserved" and the runbook says "pool exhausted" — not one shared keyword. The other
two `api` runbooks are real but clearly further away. That single ranked number is
what the agent leans on in Chapter 7.

One thing the code skips for brevity: you don't re-embed the whole bundle every
time. Ingest runs once and only re-embeds a file when it changes, so a runbook edit
costs one `embed()` call, not a full rebuild. (Chapter 9 covers that upkeep.)

### Why this beats keyword search

- **It's robust to wording.** The incident and the runbook can describe the same
  failure in totally different words and still match. You stop needing to guess the
  exact term someone used when they wrote the doc.
- **It ranks.** You don't get 40 undifferentiated hits; you get the closest matches
  first, with a score.
- **It needs no upfront tagging of every phrase.** You don't maintain a synonym list
  mapping "slots reserved" to "pool exhausted." The model already knows they're
  related.

### Where embeddings fall short

Embeddings are a good tool, not a magic one, and it's worth knowing the edges:

- **Garbage in, garbage out.** If a runbook's body is vague — "see the DB playbook"
  — it lands in a vague place on the map and matches poorly. The concrete-body advice
  from Chapter 4 is what makes retrieval land: the real error strings, the real
  commands.
- **Scope still helps.** On a big corpus, filtering by `service` before the search
  keeps a database runbook for `payments` from crowding out the right one for `api`.
  That's why the `service` front-matter field earns its keep.
- **It's retrieval, not judgment.** The search finds the *most similar* runbook. A
  human (or the agent, backed by it) still decides whether it actually applies.
  Similarity is a strong hint, not a verdict.

### The part you were dreading

Here's the good news you've been waiting for since the chapter title: **you do not
have to build any of this.** Embedding models, a place to store the coordinates, the
similarity search, the ranking, keeping it in sync as runbooks change — that's a
real pipeline, and standing it up yourself is a project with a lot of sharp edges.

You don't need to. The next chapter is exactly one config line and one folder.
