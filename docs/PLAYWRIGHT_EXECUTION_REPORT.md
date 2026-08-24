<!-- Migrated from docs/QA_Documents/PLAYWRIGHT_EXECUTION_REPORT.md to docs/ root on 2026-08-04, as part of retiring the QA_Documents/ duplicate folder. Content unchanged. Summarized in docs/Test_Summary_Report.md §3; the defect below is filed as docs/Defect_Report.md DEF-004. -->

# Playwright Execution Report — OMS-360

**Status: ONE REAL RUN RECORDED (2026-08-03), against `http://localhost:8000`
with the Docker Compose stack healthy.** Numbers below are exactly what was
reported back from that run — nothing here is estimated. A second run, to
confirm the health-spec fix (see §2) holds, has not been executed or
reported back yet; §1's numbers are the last confirmed run until then.

## 1. Summary — run #1 (2026-08-03, before the health-spec fix)

| Metric | Value |
|---|---|
| Total Tests | 142 |
| Passed | 141 |
| Failed | 1 |
| Skipped | 0 |
| Duration | *(not reported — not recorded here rather than estimated)* |
| Environment | `http://localhost:8000` (local Docker Compose stack: MySQL, Zookeeper, Kafka, oms360-engine, oms360-consumer — all confirmed healthy at run time) |
| Browser | Chromium (Desktop Chrome profile) |

## 2. Failure and root cause — run #1

**`tests/api/health.spec.ts › GET /health returns overall status + dependency map`**

- **Classification: test-authoring defect, not an application defect.** The
  test asserted `body.dependencies` contains a key named `kafka`. It does
  not, and never did — the assertion was grounded in
  `app/schemas.py::SystemHealthResponse`'s illustrative docstring example
  (`{"database": "UP", "kafka": "UP", "application": "UP", ...}`) rather
  than the real `health()` route handler in `app/routes/health.py`.
- **Real contract (confirmed by reading `app/routes/health.py`'s `health()`
  handler directly, then cross-checked against this real run):** the
  `dependencies` dict has 13 keys — `application`, `database`,
  `kafka_broker`, `kafka_producer`, `kafka_consumer_group`, `disk`,
  `memory`, `cpu`, `docker`, `redis`, `build_version`, `environment`,
  `db_pool`. There is no merged `kafka` key; Kafka status is intentionally
  split into three real keys.
- **Fix applied (test-only, per instruction — `app/` was not touched):**
  `tests/api/health.spec.ts` now asserts the complete, real 13-key set
  (strengthening the assertion from 3 keys checked to 13) and additionally
  asserts `kafka` is *not* present, so the test fails loudly again if the
  contract drifts in either direction in the future.
- **Not yet done:** re-running `tests/api/health.spec.ts` alone, then the
  full suite, against the live app to confirm the fix holds.

## 3. Recommendations

- Re-run `tests/api/health.spec.ts` alone first, then the full suite, and
  report back the results so this report's run #2 can be filled in with
  real numbers (see §4 for the exact commands).
- No other test in the 2026-08-03 run failed, so no other locator/timing/
  assertion/environment issue was surfaced by this run.
- Consider treating this failure as a small process lesson: when a test's
  assertion can be grounded in either a schema's illustrative *example* or
  the route handler's *actual* construction of the response, prefer the
  handler.

## 4. How to produce run #2

1. From the `playwright/` folder, with OMS-360 up and healthy:
   ```
   npx playwright test tests/api/health.spec.ts
   ```
   Confirm all 5 tests in that file pass.
2. Then run the complete suite:
   ```
   npx playwright test
   ```
   (or `RUN_PLAYWRIGHT.bat`, which does the same and opens the HTML report).
3. Send back the console summary and/or `test-results/results.json` and/or
   the `playwright-report/` folder. This report will be updated with run
   #2's real totals.

## 5. Phase 6 cross-check — Playwright vs. manual test cases

Still pending a confirmed clean run (see §4) before drawing conclusions.
Once run #2 is in, this section will identify, against
`docs/TEST_CASE_COVERAGE.md` and `docs/Test_Cases.xlsx`:

- Manual test cases with no Playwright equivalent yet
- Playwright tests covering scenarios not present in the manual test case set
- Any gap where both exist but disagree on expected behavior
