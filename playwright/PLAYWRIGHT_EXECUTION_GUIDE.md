# OMS-360 Playwright Execution Guide

This guide covers everything needed to install and run the Playwright QA
automation suite delivered in this `playwright/` folder, against the OMS-360
application running locally at `http://localhost:8000`.

This suite was built and verified (syntax, TypeScript type-check, and test
discovery) in a cloud environment that has no network access to your
`localhost`. **No test in this suite has been executed yet.** Execution must
happen on your machine, using the steps below.

## 1. Prerequisites

- Node.js 18 or newer (`node --version` to check).
- The OMS-360 stack running and healthy. From the repository root:

  ```
  START_OMS360.bat
  ```

  Confirm it reports the Engine as `HEALTHY` and that
  `http://localhost:8000/health` responds. The suite's `baseURL` is
  `http://localhost:8000` (see `playwright.config.ts`); override it with the
  `BASE_URL` environment variable if you ever run against a different host.

## 2. One-time setup

From inside this `playwright/` folder:

```
npm install
npx playwright install --with-deps chromium
```

This installs `@playwright/test` and downloads the Chromium browser build
Playwright drives. Only needs to be done once (or again after `package.json`
changes).

## 3. Running the tests

The single command that runs everything and produces the HTML report,
screenshots, traces, and video artifacts:

```
RUN_PLAYWRIGHT.bat
```

(Double-click it, or run it from a terminal inside the `playwright/`
folder.) It checks `/health`, installs dependencies if missing, runs the
full suite, and opens the HTML report automatically.

### Equivalent manual commands

If you prefer to run things yourself instead of the `.bat` file:

```
npx playwright test                     REM run everything
npx playwright test --grep @smoke       REM fast sanity subset only
npx playwright test --grep @regression  REM full regression pack
npx playwright test tests/api           REM API tests only
npx playwright test tests/dashboard     REM dashboard UI tests only
npx playwright test tests/e2e           REM end-to-end business-flow tests
npx playwright show-report              REM re-open the last HTML report
```

`npm run` scripts wrapping the same commands are defined in `package.json`
(`npm test`, `npm run test:smoke`, `npm run test:api`, etc.).

## 4. Where the results go

| Artifact | Location |
|---|---|
| HTML report | `playwright-report/index.html` |
| Screenshots (failures only) | `test-results/<test-name>/test-failed-1.png` |
| Videos (failures only) | `test-results/<test-name>/video.webm` |
| Traces (first retry only) | `test-results/<test-name>/trace.zip` |
| Machine-readable summary | `test-results/results.json` |

Open a trace file with `npx playwright show-trace test-results/<...>/trace.zip`.

Note on traces: Playwright only captures a trace when a test is **retried**
(`trace: 'on-first-retry'` in `playwright.config.ts`, with `retries: 1`
configured locally). A test that fails on its first and only attempt still
gets a screenshot and video, but a trace only appears if the retry also
fails. This matches the task's request for "trace on first retry" literally.

## 5. After running: send results back

Per the QA task instructions, no pass/fail numbers are reported anywhere in
this deliverable (`PLAYWRIGHT_REVIEW.md`, `docs/QA_Documents/PLAYWRIGHT_EXECUTION_REPORT.md`)
because the suite has not been executed. After you run `RUN_PLAYWRIGHT.bat`,
send back:

- The console summary (pass/fail/skip counts Playwright prints at the end), and/or
- `test-results/results.json`, and/or
- The `playwright-report/` folder (zip it if convenient).

so the execution report and coverage cross-check can be completed with real
numbers rather than estimates.

## 6. Troubleshooting

- **"Error: browserType.launch: Executable doesn't exist"** - run
  `npx playwright install --with-deps chromium` again.
- **Every test fails immediately with a connection error** - OMS-360 isn't
  running or isn't on port 8000. Re-run `START_OMS360.bat` and check
  `http://localhost:8000/health` in a browser first.
- **AI Copilot tests are skipped** - this happens when `COPILOT_ENABLED` is
  false or the intent/learning-topic catalog is empty; the tests are
  designed to skip gracefully rather than fail in that case (see
  `PLAYWRIGHT_REVIEW.md`).
