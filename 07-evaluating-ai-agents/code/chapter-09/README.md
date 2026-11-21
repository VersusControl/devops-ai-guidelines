# Chapter 9 - Turn Scores into a Benchmark

This folder scores a pinned cohort instead of one run. It reads
[manifest.json](manifest.json), separates active cases from expired and historical
ones, runs each active case several times, and writes one report with a cohort
fingerprint.

`replay/attempts-*.json` are deterministic scoring fixtures. They let the chapter
run without model calls, and they demonstrate the aggregation rules. They are not
evidence about a live model. Use the live commands below with your own keys to
replace them with real attempts.

1. Activate `ai-agent` (Python 3.10 or newer) and install
   [requirements.txt](requirements.txt). Fill the ignored `.env` from
   [.env.example](.env.example).

2. Score the recorded replay without any key:

   ```bash
   python run_benchmark.py \
     --replay replay/attempts-baseline.json \
     --runs 3 --report reports/benchmark-baseline.json
   python run_benchmark.py \
     --replay replay/attempts-candidate.json \
     --runs 3 --report reports/benchmark-candidate.json
   python compare.py \
     reports/benchmark-baseline.json \
     reports/benchmark-candidate.json
   ```

3. Run the real agent and Jev against the same cohort:

   ```bash
   python run_benchmark.py --variant baseline --runs 3
   python run_benchmark.py --variant candidate --runs 3
   ```

   Every active case gets the same number of attempts. A failed attempt is still
   an attempt. An `incomplete` or `error` attempt makes the command exit nonzero
   because the report is not a complete benchmark.

4. Inspect an expiry drill. This scores nothing and exits nonzero because the
   active set is no longer representable:

   ```bash
   python run_benchmark.py \
     --replay replay/attempts-baseline.json \
     --runs 3 --today 2027-01-01 \
     --report reports/expiry-drill.json
   ```

5. Run the offline tests:

   ```bash
   python -m unittest test_benchmark.py
   ```

The manifest owns the pinned set and its policy. A case's file content, status,
and coverage label feed the fingerprint. Changing any of them means the next
report must be produced from the new cohort; an old report cannot be compared to
a new one. Historical cases stay in the repository for audit and never enter a
score.
