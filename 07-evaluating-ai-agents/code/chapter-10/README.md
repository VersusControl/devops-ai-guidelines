# Chapter 10 - Close the Loop

This folder turns a saved miss into a reviewed case, adds it to the pinned cohort,
and keeps retirement history when a case stops representing the system.

The cache-stampede incident is a synthetic drill, like the other incidents in this
book. [misses/checkout-cache-stampede.json](misses/checkout-cache-stampede.json)
is the saved wrong answer. [inbox/checkout-cache-stampede.json](inbox/checkout-cache-stampede.json)
is the reviewed draft: the recorded situation plus the answer key a human wrote
from the evidence, not from the model's answer. The registered copy is in
[scenarios](scenarios).

1. Activate `ai-agent` and install [requirements.txt](requirements.txt).

2. Validate the draft without writing anything:

   ```bash
   python register_case.py \
     inbox/checkout-cache-stampede.json \
     --covers cache_stampede --today 2026-11-07
   ```

   The draft must name an owner, a future review date, nonempty assumptions, and
   a source record. It must also contain a distraction that is visible after the
   alert. A missing or stale review field fails before registration.

3. Register it. This copies the draft into `scenarios/`, appends an active case to
   [manifest.json](manifest.json), and adds its coverage label:

   ```bash
   python register_case.py \
     inbox/checkout-cache-stampede.json \
     --covers cache_stampede --today 2026-11-07 --apply
   ```

4. Retire or replace a case when its topology, runbook, or tool contract changes:

   ```bash
   python retire_case.py \
     --manifest manifest-before.json \
     --id pool-2025 \
     --reason "Superseded by the 2026 pool recording" \
     --owner "checkout on-call" --replaced-by pool \
     --today 2026-11-07
   ```

   Retirement moves the case to `historical`, writes who reviewed it and why, and
   keeps its file. It never deletes the evidence.

5. Score the new four-case cohort from the recorded replay, then run the tests:

   ```bash
   python run_benchmark.py \
     --replay replay/attempts-after-registration.json \
     --runs 3 --report reports/benchmark-after-registration.json
   python -m unittest test_lifecycle.py test_benchmark.py
   ```

`manifest-before.json` is the cohort before the cache case was added and before
the old pool recording was retired. It documents the change; the runnable
manifest is the four-case cohort.
