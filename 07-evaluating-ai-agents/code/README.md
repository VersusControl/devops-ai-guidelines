# Evaluating AI Agents — code

The codebase for the book **Evaluating AI Agents**. It grows one chapter at a
time. You start here with a tiny incident-diagnosis agent; later chapters add
the harness that measures it.

## Requirements

- Python 3.9 or newer. No third-party packages — everything here is standard
  library.

## Chapter 1 — build the agent

Three files:

- `tools.py` — the four read-only tools the agent can call (metrics, logs,
  deploys, db status), returning recorded data for one incident.
- `agent.py` — the agent: a loop that calls tools and commits to a
  `Conclusion` (root cause, category, evidence, trajectory).
- `run_once.py` — run the agent once with a scripted model and print the result.

Run it:

```bash
python run_once.py
```

You'll get a conclusion on screen — and no way to tell whether it's right. That
gap is what the rest of the book closes.
