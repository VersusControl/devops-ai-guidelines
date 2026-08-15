# Chapter 2 — Grade Your Agent Against a Known Answer

Self-contained. Run it from this folder without touching any other chapter.

```bash
python grade_once.py
```

## Files

| File | What it is |
|---|---|
| `agent.py` | The agent from Chapter 1, unchanged. |
| `tools.py` | The four read-only tools from Chapter 1, unchanged. |
| `answer.py` | New. `AnswerKey` — the truth we already know, here just `true_category`. |
| `grade.py` | New. `grade(conclusion, answer)` — one comparison, pass or fail. |
| `grade_once.py` | New. Runs three agents against the same incident and grades each. |

## What you should see

```text
--- careful agent ---   PASS   checks deploys + db status, blames the deploy
--- hasty agent ---     FAIL   reads only logs, blames the payment-provider blip
--- lucky agent ---     PASS   checks nothing, guesses "deploy", still passes
```

The lucky agent passing is deliberate. A category-only grade can't tell a
diagnosis from a guess — that hole is what Chapter 6 closes by grading the
evidence and the trajectory too.
