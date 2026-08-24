# 19 — Jenkins Pipeline — OMS-360 Enterprise QA

**Consolidated:** 2026-08-04 (renumbered from `docs/JENKINS_PIPELINE.md`,
content unchanged).

## Execution flow (must match Newman/Allure docs exactly)

1. The application is started **separately**, via `START_OMS360.bat`, on
   whatever machine hosts the stack this Jenkins agent targets.
2. Jenkins's **Health Check** stage verifies Docker containers healthy,
   Kafka running, MySQL available, and FastAPI responding - using the exact
   same `postman/verify_stack_health.py` script `Run_QA_Pipeline.bat` uses,
   so local runs and CI runs follow one identical flow.
3. If that verification fails, the build fails **immediately** with:
   > Application is not running. Execute START_OMS360.bat and verify all
   > services before running the QA pipeline.
4. Only if healthy does the pipeline run Newman, then pytest, then generate
   and publish the Allure report.

**This pipeline never runs `docker compose up` and never starts Docker
Desktop** - deliberately. One operational consequence worth knowing: since
Jenkins doesn't start the stack, the Jenkins agent must either run on the
same machine where `START_OMS360.bat` was already executed, or `BASE_URL`
must point at a remote host where the stack is already up and reachable
from the agent. A Jenkins agent that provisions a fresh, empty VM per build
will always fail Health Check unless something outside this pipeline starts
the stack for it first.

## What this is

`jenkins/Jenkinsfile` - a declarative pipeline for a Windows Jenkins agent
that runs the full QA suite end to end, publishes JUnit + Allure results
into Jenkins' own UI, archives every report even on failure, and fails the
build if the stack isn't healthy, or if Newman or pytest reported any
failure. It only orchestrates existing/new QA tooling - it never modifies
application code, Docker images, Kafka config, or Playwright, and it never
starts or stops the application stack. It also never opens a browser or
dashboard and never triggers another build - the "Open Jenkins Dashboard?"
prompt is a `Run_QA_Pipeline.bat`-only, local, interactive convenience
with no CI equivalent.

**Single source of truth (2026-08-04 standardization):** this Jenkinsfile
uses only relative, repo-relative paths (the Jenkins workspace root, set
by `checkout scm`) - no hardcoded project location - and its "Run Newman"
stage delegates to the same `postman/run-newman.bat` script a local run
uses, rather than maintaining a second copy of the `newman run ...`
command line. Local runs (`Run_QA_Pipeline.bat`) and CI runs execute
byte-identical Newman invocations.

## Stages

| # | Stage | What it does |
|---|---|---|
| 1 | Checkout Source | `checkout scm` |
| 2 | Install Python Dependencies | `pip install -r requirements.txt`, `pip install -r requirements-test.txt` (Node/Java/Newman/Allure CLI are one-time agent setup via `Setup_QA_Environment.bat`, not reinstalled every build) |
| 3 | Health Check | Runs `postman/verify_stack_health.py --base-url %BASE_URL%` (Docker containers / Kafka / MySQL / FastAPI) - **never** runs `docker compose up`. Fails immediately with the exact required message if unhealthy. On success, clears `allure-results/` for a fresh run |
| 4 | Run Newman | Delegates to the one canonical Newman runner, `postman/run-newman.bat` (`dir('postman') { bat 'call run-newman.bat' }`), rather than reimplementing the command inline — exports CLI/JSON/HTML Extra/JUnit into `postman/reports/` and raw Allure results into `allure-results/`, exactly as a local run does |
| 5 | Publish JUnit XML | `junit testResults: 'postman/reports/newman-junit-report.xml'` - surfaces per-request pass/fail in Jenkins' native test-result UI/trend graph |
| 6 | Archive Newman Reports | `archiveArtifacts 'postman/reports/**'` |
| 7 | Execute pytest | `python -m pytest --alluredir=allure-results` - adds to the same `allure-results/` Newman just wrote into |
| 8 | Generate Allure Results | Copies `allure-report/history/` (from the previous build, if the workspace persisted it) into `allure-results/history/`, then runs `generate_allure_metadata.py` for `environment.properties`/`executor.json`/`categories.json` |
| 9 | Generate Allure HTML Report | `allure generate allure-results -o allure-report --clean` - exit code checked explicitly; the stage (and build) fails immediately, printing the Allure CLI's own error, if generation fails |
| 10 | Apply Allure Dark Theme | `postman/apply_allure_dark_theme.py` - cosmetic, non-fatal (`\|\| exit 0`); re-applies a dark-theme-by-default snippet into `allure-report/index.html`'s own official head-customization slot every build, since `--clean` rewrites `index.html` from scratch each time. Never overrides a viewer's own later theme toggle. |
| 11 | Verify Allure Report Integrity | `postman/verify_allure_report.py` - read-only structural check that raw results, the 3 metadata files, and the generated `allure-report/` (index.html, `data/*.json`, `widgets/*.json`) all actually exist and are non-empty/valid, catching a report that "generated" but is incomplete |
| 12 | Publish Allure Report | `allure(...)` pipeline step - **requires the Allure Jenkins plugin**; renders the trend graph and report link directly on the build page |
| 13 | Archive HTML Reports | `postman/reports/newman-html-report.html`, `allure-report/**` |
| 14 | Archive JSON Reports | `postman/reports/newman-json-report.json` |
| 15 | Archive JUnit XML | `postman/reports/newman-junit-report.xml` |
| 16 | Archive Allure Report | `allure-report/**`, `allure-results/**` |

`post { always { ... } }` republishes JUnit results and re-archives
whatever report files exist (each guarded with `fileExists()`) as a safety
net - so even if stage 3 (Health Check), stage 4 (Run Newman), stage 7
(Execute pytest), stage 9 (Generate Allure HTML Report), or stage 11
(Verify Allure Report Integrity) fails and the pipeline jumps straight past
the later Publish/Archive stages, whatever reports were produced up to that
point are still published and captured. There is deliberately **no**
`docker compose down` in `post{}` either - this pipeline never started the
stack, so it never stops it; the stack's lifecycle belongs entirely to
`START_OMS360.bat`/`STOP_OMS360.bat`.

## Why the build fails on a failing check or test

- Health Check: `verify_stack_health.py` exits non-zero if Docker/Kafka/
  MySQL/FastAPI aren't all confirmed healthy - the `bat` step fails that
  stage and stops the pipeline before any test runs.
- Newman: its own process exit code is non-zero if any `pm.test()`
  assertion fails - the `bat` step in "Run Newman" propagates that to
  Jenkins, which fails the stage.
- pytest: a non-zero exit code in "Execute pytest" fails that stage the
  same way.
- Generate Allure HTML Report: if `allure generate` itself fails (bad Java
  install, corrupt result file, disk full, etc.), its exit code is checked
  explicitly and the stage fails immediately with the Allure CLI's own
  error printed above - the pipeline never falls through to Publish/Archive
  with a missing or partial report.
- Verify Allure Report Integrity: even when `allure generate` exits 0, this
  stage independently confirms the output is actually complete (real data
  files behind Overview/Suites/Behaviors/Categories/Timeline/Environment) -
  if anything's missing or empty, this stage fails with the exact file and
  reason.
- In every case, reports produced so far are still published/archived via
  `post { always { ... } }`, per explicit requirement - only the *build
  result* (pass/fail) is affected, never report availability.

## One-time setup (per Jenkins agent)

Run `Setup_QA_Environment.bat` once on the agent machine (or bake its
checks into your agent image), or ensure manually:
- Windows agent with Python 3.11+, Node.js/npm, Docker Desktop/Engine with
  `docker compose` v2 already **running the OMS-360 stack** (started via
  `START_OMS360.bat` - this pipeline does not start it).
- Newman, `newman-reporter-htmlextra`, `newman-reporter-allure`, and the
  Allure commandline installed globally (`npm install -g newman
  newman-reporter-htmlextra newman-reporter-allure allure-commandline`).
- The **Allure Jenkins plugin** installed on the Jenkins controller (for
  the "Publish Allure Report" stage - comment that stage out if you don't
  want to install the plugin; the static `allure-report/` folder is still
  archived regardless via the Archive stages).

## Jenkins execution

The pipeline runs automatically on whatever trigger you configure (SCM
webhook, polling, or manual "Build Now"), **as long as the stack is already
running** on the target machine (step 1 of the execution flow above - not
something this pipeline does for you). Build results appear on the build
page:
- **Test Result Trend** (from "Publish JUnit XML")
- **Allure Report** link (from "Publish Allure Report", if the plugin is
  installed)
- **Build Artifacts** listing every archived report (from the Archive
  stages / `post{always{}}`)

If Health Check fails, the build turns red immediately with the exact
"Application is not running..." message in the console log - no Newman or
pytest stage runs at all, and no reports are generated for that build
(there's nothing to report on yet).

## Report locations (on the agent workspace, then archived into the build)

| Report | Workspace path | Archived as |
|---|---|---|
| Newman CLI/JSON/HTML/JUnit | `postman/reports/` | Build artifact + JUnit trend |
| Allure raw results | `allure-results/` | Build artifact |
| Allure HTML report | `allure-report/` | Build artifact + Allure plugin page |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Build fails at "Health Check" with "Application is not running..." | The stack isn't up (or isn't fully healthy yet) on the machine this agent targets | Run `START_OMS360.bat` on that machine and confirm `docker compose ps` shows every container healthy, then re-trigger the build - this pipeline will never start it for you |
| "Publish Allure Report" stage fails with "no such DSL method 'allure'" | Allure Jenkins plugin not installed | Install it from the Jenkins Plugin Manager, or comment out that stage - archiving still works without it |
| Health Check passes locally but fails from Jenkins | The Jenkins agent can't reach `BASE_URL` (different host/network than where you tested manually) | Set the `BASE_URL` environment variable in the Jenkinsfile (or agent config) to a URL the agent can actually reach |
| `junit` step fails with "no test report files were found" | `postman/reports/newman-junit-report.xml` wasn't produced - Newman likely crashed before writing reporters | Check the "Run Newman" stage's console output for the underlying Newman error |
| Trend graph resets every build | Agent workspace is wiped between builds (no persistent `allure-report/history/` to copy forward) | Either don't wipe the workspace between builds, or archive/restore `allure-report/history/` explicitly as its own artifact between builds |
| Build always fails at "Install Python Dependencies" | No network access from the agent to PyPI | Configure an internal PyPI mirror/proxy, or pre-bake the venv into the agent image |
| This Jenkinsfile has not been run against a real Jenkins controller | Not yet execution-tested in this environment | Review agent labels (add `agent { label 'windows' }` if you use labeled agents) and the Allure plugin availability before relying on it in production CI |
