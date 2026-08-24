# 18 — Allure Setup — OMS-360 Enterprise QA

**Consolidated:** 2026-08-04 (renumbered from `docs/ALLURE_SETUP.md`,
content unchanged).

## Execution flow (must match Newman/Jenkins docs exactly)

1. `START_OMS360.bat` - starts the app; verifies Docker containers healthy,
   Kafka running, MySQL available, FastAPI responding.
2. `Setup_QA_Environment.bat` - one time per machine.
3. `Run_QA_Pipeline.bat` (or `Generate_Allure_Report.bat` for pytest-only) -
   daily. Re-verifies the same four things first (`postman/verify_stack_health.py`)
   and fails immediately, without starting anything, if they aren't already true.
4. Jenkins mirrors this exact flow (`docs/19_Jenkins_Pipeline.md`) - it never
   runs `docker compose up` either.

## What this is

A unified Enterprise Allure report combining **both**:
- the existing `tests/` pytest suite (`test_health.py`, `test_inventory.py`,
  `test_orders.py`, `test_sql_validation.py`, `tests/api/`, `tests/ai/`,
  `tests/integration/`) - via `allure-pytest`, no test file modified; and
- the Newman/Postman API collection - via `newman-reporter-allure`;

both write their raw results into the same `allure-results/` directory, so
one `allure generate` produces one report covering the whole QA surface.

```
pytest.ini                       testpaths=tests, --alluredir=allure-results
requirements-test.txt            allure-pytest, pytest-html (requirements.txt untouched)
postman/verify_stack_health.py   Docker/Kafka/MySQL/FastAPI verification - never starts anything
postman/generate_allure_metadata.py   writes environment.properties / executor.json / categories.json
postman/verify_allure_report.py  read-only integrity check of allure-results/ + allure-report/ output
postman/apply_allure_dark_theme.py  makes dark theme the report's default for first-time visitors
allure-results/                  raw results - Newman's + pytest's + history/ + the 3 metadata files
allure-report/                   generated static HTML report (History/Trend/Timeline/Suites/
                                  Packages/Behaviors/Categories/Executor/Environment/Retries/Summary/Statistics)
Generate_Allure_Report.bat       pytest -> preserve history -> generate metadata -> allure generate
                                  (stops immediately, printing the exact error, if generate fails) ->
                                  apply_allure_dark_theme.py -> verify_allure_report.py
Run_QA_Pipeline.bat              verify -> Newman -> Generate_Allure_Report.bat -> allure open allure-report
```

## IMPORTANT - always open the report with `allure open`, never by double-clicking index.html

`allure-report/index.html` is a static file, but the report is a
JavaScript single-page app that loads its actual content (Suites,
Behaviors, Categories, Timeline, Environment, etc.) via `fetch()` calls to
JSON files under `allure-report/data/` and `allure-report/widgets/` at
runtime.

If you open `index.html` directly - by double-clicking it in File
Explorer, or via a script that runs `start allure-report\index.html` - the
browser loads it over the `file://` protocol. Browsers block a page's own
`fetch()` calls to sibling files under `file://` as a CORS security
restriction. The visible symptom is exactly what a blank page or a
**"500 Failed to fetch"** message on an otherwise successfully-generated
report - it is not a sign the report itself is broken or that
`allure generate` failed.

The fix is always the same: run

```bat
allure open allure-report
```

which serves the exact same files over a real local HTTP server (default
`http://127.0.0.1:PORT`) and opens that URL in your browser - `fetch()`
calls to same-origin `http://` URLs are not blocked, so every tab loads
correctly. `Run_QA_Pipeline.bat` now runs this for you automatically on
success (in its own window, which stays open serving the report - leave it
running while you browse); if you generate the report some other way,
run `allure open allure-report` yourself instead of opening `index.html`.

## Dark theme by default

The report opens in **dark theme** for first-time visitors, applied by
`postman/apply_allure_dark_theme.py` right after every `allure generate`
(re-applied every run, since `--clean` rewrites `index.html` from scratch
each time). Confirmed by reading the real generated report bundle: Allure
remembers a viewer's theme choice in the browser via
`localStorage["allure-theme"]`, falling back to the OS `prefers-color-scheme`
setting when nothing is stored yet. This script sets that key to `"dark"`
only if nothing is already stored, so it never overrides your own later
click on the theme toggle in the report's sidebar - your choice sticks
across reloads in that same browser, exactly like using the toggle
manually. This step is cosmetic and non-fatal - if it can't run for any
reason, the report still generates and opens normally, just using
Allure's own default theme behavior instead.

## Enterprise report features

Everything Allure builds automatically from the raw results needs no extra
config: **Suites, Packages, Behaviors, Retries, Summary, Statistics**. Three
things need small, explicit files - all handled automatically by
`generate_allure_metadata.py`:

| Feature | File | What it shows |
|---|---|---|
| Environment tab | `allure-results/environment.properties` | App version/build/environment (live-probed from `GET /version` and `/health`), OS, Python/Node/Newman/Allure versions, run timestamp |
| Executor info | `allure-results/executor.json` | "Local Execution" locally, or Jenkins build name/number/URL when `JENKINS_URL`/`BUILD_NUMBER`/`BUILD_URL` env vars are present |
| Categories tab | `allure-results/categories.json` | Custom failure grouping - Business Rule Violations, Infrastructure (DB/Kafka unreachable), API Contract Failures, Timeouts, Unhandled/Internal Errors, Test Defects - grounded in this project's real `app/core/exceptions.py` error codes |
| History / Trend / Timeline | `allure-results/history/` | Copied forward from the previous `allure-report/history/` before every `allure generate` - see below |

## One-time setup

```bat
Setup_QA_Environment.bat
```

Installs the Allure commandline via `npm install -g allure-commandline`
(bundles the CLI - still needs Java, which the same script verifies
separately). Also installs `requirements-test.txt`
(`allure-pytest`, `pytest-html`) on top of the app's own `requirements.txt`
(never modified).

**Why base runtimes aren't silently auto-installed:** Node.js, Java, and
Python are foundational OS-level runtimes. Auto-downloading and silently
executing an installer for one of those means running an arbitrary binary
with no human confirming its source, version, or CPU architecture - not a
safe default for a generated script. `Setup_QA_Environment.bat` verifies
each and prints the official download link if missing; everything
npm-installable (Newman, its two reporter plugins, the Allure CLI) is
auto-installed since `npm install` is the standard, safe path once Node/npm
are already present.

## Daily execution

```bat
Generate_Allure_Report.bat
```

or, for the full suite including Newman:

```bat
Run_QA_Pipeline.bat
```

Either way, this NEVER installs software - only `Setup_QA_Environment.bat`
does. `Generate_Allure_Report.bat`'s exit code reflects pytest's result
(`0` if every test passed) **only if** `allure generate` and the
integrity verification both also succeeded - if either of those fails,
the script prints the exact error and stops immediately with that step's
own non-zero exit code instead, per explicit requirement (see "If
generation fails" in the header of `Generate_Allure_Report.bat`).

To view the report interactively, see the "IMPORTANT" section above -
always `allure open allure-report`, never open `index.html` directly.
`Run_QA_Pipeline.bat` now does this for you automatically on success.

## How history/trend preservation works (do NOT overwrite history)

Every run:
1. `allure-results/` is cleared (this run's raw results only - not history).
2. Newman and pytest both write fresh raw results into it.
3. **Before** generating, the *previous* report's `allure-report/history/`
   folder is copied into `allure-results/history/`.
4. `allure generate allure-results -o allure-report --clean` runs.
   `--clean` only wipes the **output** folder (`allure-report/`) - by the
   time it runs, this run's history is already sitting safely inside the
   **input** folder (`allure-results/`), so `allure generate` picks it up
   and extends the trend rather than resetting it.

This is the standard Allure trend-preservation pattern - raw per-test result
files don't need to be kept forever; the small `history/` folder is what
carries multi-run trend data forward.

## Why some `tests/api/` and `tests/integration/` cases may show as failed/skipped

Some existing suite cases expect a live stack (MySQL + Kafka + the FastAPI
app) - if `docker compose up -d` / `START_OMS360.bat` wasn't run first,
those specific tests fail or error as expected, visible clearly in the
report rather than hidden.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `allure-report/index.html` shows a blank page or **"500 Failed to fetch"** | Opened `index.html` directly (double-click, or a script using `start allure-report\index.html`) - the browser loaded it over `file://`, which blocks the report's own `fetch()` calls to `data/*.json`/`widgets/*.json`. This does **not** mean the report failed to generate - see the "IMPORTANT" section above | Run `allure open allure-report` instead. `Run_QA_Pipeline.bat` now does this automatically |
| `'allure' is not recognized...` | Allure CLI not installed | Run `Setup_QA_Environment.bat` |
| Pipeline stops immediately with "Application is not running..." | Stack not started, or not yet healthy | Run `START_OMS360.bat` first - `Run_QA_Pipeline.bat`/`Generate_Allure_Report.bat` (via Newman's stage) verify but never start the stack themselves |
| `Generate_Allure_Report.bat` stops with `[ERROR] "allure generate ..." FAILED` | `allure generate` itself returned a non-zero exit code (Java error, corrupt result file, disk full, etc.) | The exact Allure CLI error is printed directly above this message - fix the underlying cause (see the Java-error row below), then re-run |
| `Generate_Allure_Report.bat` stops with `[ERROR] Allure report failed integrity verification` | `postman/verify_allure_report.py` found the generated `allure-report/` incomplete (missing/empty `index.html`, `data/*.json`, or `widgets/*.json`) even though `allure generate` exited 0 | Check the `[FAIL]` line(s) printed above for the exact missing file; re-run `Generate_Allure_Report.bat` - if it recurs, check disk space and that `allure-results/` actually has result files (Step 1 of the verifier output) |
| `allure generate` fails with a Java error | Java missing/misconfigured | Verify `java -version`; reinstall from https://adoptium.net/ |
| Report has no Trend/History graph | First-ever run (nothing to carry forward yet) - expected | Run the pipeline again; the graph appears from the 2nd run onward |
| Trend graph looks reset / history missing | `allure-report/history/` didn't exist yet, or `allure-report/` was manually deleted | This is expected after deleting `allure-report/` - history only survives if that folder existed before the run |
| Environment tab shows "unreachable" for app fields | Stack wasn't running when `generate_allure_metadata.py` ran | Make sure `START_OMS360.bat` was run before the pipeline - metadata generation is best-effort and non-fatal, so the report still generates either way |
| Categories tab is empty / shows "Uncategorized" | A failure's message didn't match any regex in `categories.json` | Expected for novel failure types - the category list covers this project's known real error codes, not every possible message |
| `requirements-test.txt` install fails | No network access, or `requirements.txt` itself failed first | Run `pip install -r requirements.txt` manually first to isolate which file is failing |
