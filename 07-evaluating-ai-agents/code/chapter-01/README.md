# Chapter 1 — Build the AI Agent This Book Runs On

Self-contained. Run it from this folder.

```bash
python run_once.py
```

## Files

| File | What it is |
|---|---|
| `tools.py` | The four read-only tools the agent can call (metrics, logs, deploys, db status), returning recorded data for one incident. |
| `agent.py` | The agent: a loop that calls tools and commits to a `Conclusion` (root cause, category, evidence, trajectory). |
| `run_once.py` | Runs the agent once with a scripted model and prints the result. |

## What you should see

A confident diagnosis — and no way to tell whether it's right. That gap is what
the rest of the book closes, starting in Chapter 2.
