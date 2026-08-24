# 17 — Newman / Postman Setup — OMS-360 Enterprise QA

**Consolidated:** 2026-08-04 (renumbered from `docs/NEWMAN_SETUP.md`,
content unchanged).

## Execution flow (must match Allure/Jenkins docs exactly)

1. Start the application: `START_OMS360.bat`.
2. That step verifies Docker containers are healthy, Kafka is running,
   MySQL is available, and FastAPI responds - if you skip it, everything
   below fails fast (see step 4).
3. One time per machine: `Setup_QA_Environment.bat`.
4. Daily: `Run_QA_Pipeline.bat`. It re-verifies the same four things via
   `postman/verify_stack_health.py` before touching Newman or pytest - if
   the stack isn't up, it stops immediately with:
   > Application is not running. Execute START_OMS360.bat and verify all
   > services before running the QA pipeline.
5. Jenkins follows the identical flow (see `docs/19_Jenkins_Pipeline.md`) -
   neither this script nor Jenkins ever runs `docker compose up` or starts
   Docker Desktop themselves. Verification only.

## What this is

An enterprise regression suite covering every real FastAPI endpoint in OMS-360,
generated directly from live route source (`app/routes/*.py`, `app/api/ai/*.py`).
No fabricated or placeholder APIs.

```
postman/
  collection/OMS360.postman_collection.json   50 real API requests, 6 folders + 1 optional HTML-smoke folder
  environment/OMS360.postman_environment.json baseUrl + chained variables
  package.json                                npm deps: newman, newman-reporter-htmlextra, newman-reporter-allure
  run-newman.bat                              CLI + JSON + HTML Extra + JUnit XML + Allure-raw runner
  generate_allure_metadata.py                 writes environment.properties/executor.json/categories.json
  reports/                                    generated on each run - CLI/JSON/HTML/JUnit
```

## Collection structure

| Folder | Requests | Notes |
|---|---|---|
| 01 - Health & Metrics | 4 | `/`, `/version`, `/health`, `/metrics` |
| 02 - Orders | 4 | create/list/get/audit - creates a real order and chains `order_id` |
| 03 - Inventory | 9 | list/low-stock/out-of-stock/alerts/history/get/restock/update/create - chains `item_id` |
| 04 - Dashboard | 8 | Operations + Monitoring Center aggregate JSON endpoints |
| 05 - AI Runtime | 8 | 7 endpoints, `/config` exercised twice (default + `?capability=`) |
| 06 - AI Copilot | 18 | business Q&A, intents, executive summary, insights, root cause, QA/docs/learning assistants - chains `intent` and `learning_topic` |
| 07 - Dashboard Pages (HTML Smoke) | 5 | registered page routes that serve HTML, not JSON - kept separate, status-code checks only |

51 JSON API requests (50 unique endpoints - `/api/v1/ai/config` is tested
twice, plain and with `?capability=rag_enabled`) + 5 HTML smoke checks = 56
requests, 168 `pm.test()` assertions.

---

## One-time setup

Run once per machine:

```bat
Setup_QA_Environment.bat
```

This verifies Node.js, npm, Java, Python, pip, and auto-installs (via npm)
anything missing among: Newman, `newman-reporter-htmlextra`,
`newman-reporter-allure`, and the Allure CLI (`allure-commandline`). It also
installs `requirements-test.txt` (pip skips anything already satisfied - safe
to re-run). See `docs/18_Allure_Setup.md` for why base runtimes (Node/Java/
Python) are verified-and-linked rather than silently auto-installed.

## Daily execution

The stack must be up first:

```bat
START_OMS360.bat
```

Then, from the repo root:

```bat
Run_QA_Pipeline.bat
```

This first verifies the stack via `postman/verify_stack_health.py` (Docker
containers, Kafka, MySQL, FastAPI) - it does **not** start Docker or the app
itself. If the stack isn't already up, it stops immediately with:
> Application is not running. Execute START_OMS360.bat and verify all
> services before running the QA pipeline.

Once verified, it runs Newman AND pytest, merges both into one Allure
report, and opens the reports automatically on success.
`Run_QA_Pipeline.bat` performs only verification, test execution, and
report generation - it never installs anything (only
`Setup_QA_Environment.bat` does) and never starts the stack (only
`START_OMS360.bat` does).

To run **only** Newman (no pytest/Allure):

```bat
cd postman
run-newman.bat
```

This produces, inside `postman/reports/`:
- **CLI report** - `newman-cli-report.txt` (full console output, teed via PowerShell)
- **JSON report** - `newman-json-report.json` (machine-readable)
- **HTML Extra report** - `newman-html-report.html` (dark-themed)
- **JUnit XML report** - `newman-junit-report.xml` (for CI test-result publishers)

...and raw Allure result files into the repo-root `allure-results/` (merged
there with pytest's own results - see `docs/18_Allure_Setup.md`).

Exit code is Newman's own: `0` if every assertion passed, non-zero otherwise.

## Jenkins execution

See `docs/19_Jenkins_Pipeline.md` - as of the 2026-08-04 standardization
pass, the "Run Newman" stage delegates directly to this same
`postman\run-newman.bat` script (`dir('postman') { bat 'call run-newman.bat' }`)
instead of reimplementing the `newman run ...` command line a second time
in the Jenkinsfile - local and CI runs execute byte-identical Newman
invocations. "Publish JUnit XML" + "Archive Newman Reports" then wire the
results into Jenkins' own UI.

`postman\run-newman.bat` is the single canonical Newman runner for this
project - nothing else invokes `newman run` directly. A former root-level
convenience wrapper, `Generate_Newman_Report.bat`, duplicated this script
without being called by anything and was removed; see
`docs/16_QA_Automation_Guide.md` §7.

## Report locations

| Report | Path |
|---|---|
| CLI log | `postman/reports/newman-cli-report.txt` |
| JSON | `postman/reports/newman-json-report.json` |
| HTML Extra | `postman/reports/newman-html-report.html` |
| JUnit XML | `postman/reports/newman-junit-report.xml` |
| Raw Allure results (Newman's share) | `allure-results/` (merged with pytest's) |
| Unified Allure HTML report | `allure-report/index.html` |

## Variable chaining

The environment starts with `item_id=ITEM-BURGER`, `intent=pending_orders`,
and `learning_topic=architecture` as safe defaults (real seed-data values),
and `order_id` empty. During a run, list/catalog requests capture real ids
from live responses into these variables for downstream detail requests -
see the collection description for the exact chain.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `'newman' is not recognized...` | Newman not installed / not on PATH | Run `Setup_QA_Environment.bat` |
| `Run_QA_Pipeline.bat` stops immediately with "Application is not running..." | Stack not started, or not yet healthy | Run `START_OMS360.bat` and confirm `docker compose ps` shows every container healthy before re-running the pipeline - this is a fail-fast check, not a wait loop |
| Every request fails with a connection error (running `run-newman.bat` directly, bypassing the pipeline's verify step) | Stack not running | `START_OMS360.bat`, wait for `/health` to return `HEALTHY` |
| `reports\newman-junit-report.xml` missing | Newman crashed before writing reporters (e.g. bad collection JSON) | Check `newman-cli-report.txt` for the actual error; re-validate the collection JSON |
| Allure report shows no Newman results, only pytest | `--reporter-allure-resultsDir` pointed at the wrong folder, or `run-newman.bat` was run from a different working directory | Always invoke `run-newman.bat` from inside `postman/` (it self-`cd`s), or use `Run_QA_Pipeline.bat` which handles paths for you |
| `newman-reporter-allure` "reporter not found" | Reporter installed locally instead of globally, or vice versa | Re-run `Setup_QA_Environment.bat` - it checks/installs globally, matching how `run-newman.bat` invokes `newman` |
| HTML report doesn't open automatically | `Run_QA_Pipeline.bat` only auto-opens on **overall success** (Newman AND pytest both passed) | Open `postman/reports/newman-html-report.html` manually to see the failure detail |
