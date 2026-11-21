# Chapter 11 - Gate Your Agent in CI

This folder turns a benchmark report into a merge gate. The gate has two parts:
quality on the active cases, and the health of the suite that produced the number.

1. Activate `ai-agent` and install [requirements.txt](requirements.txt).

2. Produce a report for the current four-case cohort. The recorded replay keeps
   the example offline; replace it with `python run_benchmark.py --variant candidate
   --runs 3` when your keys are configured:

   ```bash
   python run_benchmark.py --replay replay/ci-attempts.json --runs 3 \
     --report reports/ci-green.json
   ```

3. Gate it:

   ```bash
   python gate.py reports/ci-green.json
   ```

   A green report exits 0. A failed check prints the reason and exits 1. The gate
   fails when the report's cohort fingerprint does not match the current manifest,
   when an active case is missing from the report, when attempts are too few or
   unbalanced, when any attempt is ungraded, when the overall or per-case pass
   rate is below policy, when an active case is past review, when required
   coverage is missing, or when a retired case has not been reviewed recently.

4. Run the same report through an expiry drill. The report still contains high
   scores, but the suite is no longer the suite it scored:

   ```bash
   python gate.py reports/ci-green.json --today 2026-12-20
   ```

   To reproduce the stale-report failure, gate a report produced before the cache
   case was registered. Copy `reports/benchmark-candidate.json` from
   `code/chapter-09/` after running it, then:

   ```bash
   python gate.py reports/old-cohort.json
   ```

   The run helper refuses that replay on purpose: a three-case file cannot be
   scored against the current four-case manifest. Only a report produced earlier
   can demonstrate the mismatch.

5. Run the tests:

   ```bash
   python -m unittest test_gate.py test_benchmark.py
   ```

[ci-example.yml](ci-example.yml) is a pull-request workflow that installs the
dependencies, runs the tests, produces a live report from repository secrets, and
runs the gate. Keep provider keys in a protected environment; never put them in
the repository or in a scenario file.
