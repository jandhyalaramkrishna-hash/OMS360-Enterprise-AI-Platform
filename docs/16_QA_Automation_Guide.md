# 16 — QA Automation Guide — OMS-360

**New document, 2026-08-04**, written as part of the documentation
reorganization to give one operational runbook for the QA automation
tooling — previously this picture was split across `docs/06_Test_Strategy.md`
(the "why/what" strategy) and three separate tool-specific setup docs
(`docs/17_Newman_Setup.md`, `docs/18_Allure_Setup.md`,
`docs/19_Jenkins_Pipeline.md`). This document is the "how do I actually
run this today" quick-reference; the three tool-specific docs remain the
deep-dive references for each tool.

## 1. The Scripts, in the Order You'd Actually Use Them

| Order | Script | What it does | Run how often |
|---|---|---|---|
| 1 | `START_OMS360.bat` | Starts the application stack (MySQL, Zookeeper, Kafka, API, consumer). QA tooling never does this itself. | Every time you need the stack up |
| 2 | `Setup_QA_Environment.bat` | Verifies Node/npm/Java/Python; auto-installs Newman + its two reporter plugins + the Allure CLI; installs `requirements-test.txt` | Once per machine |
| 3 | `Run_QA_Pipeline.bat` | Verify stack health → Newman → pytest → Allure report (generate, dark-theme, verify) → `allure open` → completion banner → optional Jenkins dashboard open (Y/N, view only) | Daily / before every regression pass |
| 3a | `Generate_Allure_Report.bat` | Same as step 3 but pytest + Allure only, no Newman | When you only need the pytest side reported |
| 3b | `postman\run-newman.bat` | Newman only, no pytest/Allure | Quick API-only check |
| 4 | `CHECK_OMS360.bat` | Prints current stack/container/port status | Anytime |
| 5 | `STOP_OMS360.bat` | Stops the app layer only (infra stays up) | End of session |

## 2. What `Run_QA_Pipeline.bat` Actually Does, Step by Step

1. **Verify** — `postman/verify_stack_health.py` checks Docker containers,
   Kafka, MySQL, and FastAPI are all healthy. If not, it stops
   immediately with:
   > Application is not running. Execute START_OMS360.bat and verify all
   > services before running the QA pipeline.
   This is a fail-fast check, not a wait loop, and the pipeline never
   starts Docker or the app itself.
2. **Newman** — runs the 56-request/168-assertion Postman collection with
   5 reporters (CLI, JSON, HTML Extra, JUnit, Allure-raw).
3. **pytest** — runs the full test suite (`tests/`), writing to the same
   `allure-results/` directory Newman just wrote into.
4. **Allure generate** — copies forward the previous report's
   `allure-report/history/` (for trend continuity), runs
   `generate_allure_metadata.py` (environment/executor/categories
   metadata), then `allure generate allure-results -o allure-report --clean`.
   The exit code is checked explicitly; a failure stops the script
   immediately with the exact Allure CLI error, rather than silently
   producing a partial report.
5. **Dark theme** — `postman/apply_allure_dark_theme.py` re-applies the
   dark-theme-by-default snippet into `allure-report/index.html`'s
   official customization slot (cosmetic, non-fatal — a failure here
   never blocks the pipeline).
6. **Verify** — `postman/verify_allure_report.py` does a read-only
   structural check that the raw results, the 3 metadata files, and the
   generated report (`index.html`, `data/*.json`, `widgets/*.json`) are
   all actually present and non-empty — catching a report that
   "generated" but is silently incomplete.
7. **Open** — on success, `allure open allure-report` serves the report
   over a real local HTTP server and opens it in your browser. This
   matters: opening `allure-report/index.html` directly via `file://`
   triggers a CORS-blocked "500 Failed to fetch" even on a perfectly
   good report — see `docs/18_Allure_Setup.md` for the full explanation.
   The Newman HTML report (`postman/reports/newman-html-report.html`)
   opens automatically at the same time.
8. **Completion banner + optional Jenkins dashboard** — on success, the
   script prints:
   ```
   =================================================================
   OMS360 QA PIPELINE COMPLETED SUCCESSFULL
   =================================================================

   Reports Generated:
    - Newman HTML Report
    - Allure Report
    - JUnit XML

   Open Jenkins Dashboard? (Y/N):
   ```
   Answering `Y` opens `http://localhost:9090/` in your browser — **view
   only**. This never triggers a Jenkins build; it's purely a convenience
   link to the dashboard. Answering anything else (or `N`) skips it and
   the script exits normally. On failure, this banner and prompt are
   skipped — only the technical QA Pipeline Summary above it is shown.

## 3. Dark Theme by Default

The Allure report opens in dark theme for first-time visitors. Mechanism:
Allure stores a viewer's theme choice in the browser's
`localStorage["allure-theme"]`; `apply_allure_dark_theme.py` sets that key
to `"dark"` only if nothing is already stored, so it never overrides a
later manual toggle in the report's own sidebar. Re-applied every run
(since `--clean` rewrites `index.html` from scratch each generation).
Full detail: `docs/18_Allure_Setup.md` "Dark theme by default" section.

## 4. Report Locations

| Report | Path |
|---|---|
| Newman CLI log | `postman/reports/newman-cli-report.txt` |
| Newman JSON | `postman/reports/newman-json-report.json` |
| Newman HTML Extra | `postman/reports/newman-html-report.html` |
| Newman JUnit XML | `postman/reports/newman-junit-report.xml` |
| Raw Allure results (Newman + pytest merged) | `allure-results/` |
| Unified Allure HTML report | `allure-report/index.html` (always open via `allure open allure-report`, never double-click) |

## 5. Quick Troubleshooting

| Symptom | Fix |
|---|---|
| "Application is not running..." | Run `START_OMS360.bat`, confirm `docker compose ps` shows every container healthy, then re-run |
| `allure-report/index.html` shows "500 Failed to fetch" | You opened it directly (`file://`). Run `allure open allure-report` instead — `Run_QA_Pipeline.bat` already does this on success |
| `'newman'`/`'allure'` not recognized | Run `Setup_QA_Environment.bat` |
| `Generate_Allure_Report.bat` stops with an explicit `[ERROR]` | The exact cause is printed directly above — either `allure generate` itself failed (Java/disk issue) or `verify_allure_report.py` found the output incomplete |
| Report has no Trend/History graph | Expected on the very first-ever run — appears from the 2nd run onward |

Full tool-specific detail and troubleshooting tables: `docs/17_Newman_Setup.md`,
`docs/18_Allure_Setup.md`, `docs/19_Jenkins_Pipeline.md`.

## 6. Smoke Test Before a Full Pipeline Run

Run the 6-item smoke checklist (`docs/07_Test_Plan.md` §6.2) immediately
after `START_OMS360.bat` and before a full `Run_QA_Pipeline.bat` pass — it
takes under 2 minutes and catches a dead stack before you spend time on
the full suite.

## 7. One Newman Runner, One Allure Generator, One Pipeline (2026-08-04 standardization)

As of the 2026-08-04 QA automation standardization pass, there is exactly
one script that owns each responsibility, and nothing else duplicates it:

| Responsibility | Single canonical script |
|---|---|
| Run the Postman collection | `postman/run-newman.bat` — both `Run_QA_Pipeline.bat` and `jenkins/Jenkinsfile`'s "Run Newman" stage delegate to this exact script rather than reimplementing the `newman run ...` command line a second time |
| Generate the Allure report | `Generate_Allure_Report.bat` — the only script that calls `allure generate` |
| Run the full daily QA cycle | `Run_QA_Pipeline.bat` — the only end-to-end orchestrator |

`Generate_Newman_Report.bat` (a root-level convenience wrapper that
duplicated `postman/run-newman.bat` without being called by anything) was
removed as part of this pass — see `Cleanup_Duplicate_QA_Scripts.bat`.

**Portability:** every script in this flow uses only `%~dp0`-relative
paths and relative filenames (`docker-compose.yml`, `postman\reports\`,
`allure-results\`, etc.) — none hardcodes a drive letter or project
location, so the repository can be cloned to any path and the flow works
unmodified. Confirmed by direct inspection of every script and Python
helper in this flow; **not independently executed end-to-end from a fresh
clone in this session** (no Windows/Docker access here) — run
`Setup_QA_Environment.bat` → `START_OMS360.bat` → `Run_QA_Pipeline.bat`
from a genuinely fresh clone once to confirm on your machine.
