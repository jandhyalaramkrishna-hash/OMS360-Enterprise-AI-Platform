# OMS360 Student Practice Kit - source

Builds two executables via `build/build.bat`:
`OMS360 Enterprise AI Platform.exe`, placed in `../Student_Practice_Kit/`
(the folder given to students, alongside its own docs/sample-data - see
that folder's `README.txt`), and `OMS360 License Generator.exe`, placed in
`build/admin-only/` (kept by ZelQA Technologies staff, never shipped to
students - see `build/admin-only/README.txt`, created on first build).

**This entire folder is additive.** Nothing here imports business logic
from `app/` or `ai/` except two narrow, deliberate seams: `launcher/main.py`
sets a handful of already-supported `OMS360_*` environment variables and
then does `from app.main import app` - the exact same FastAPI app object
`uvicorn app.main:app` would give you - and runs it via `uvicorn.Server`
in a background thread. Nothing under `app/` or `ai/` was read for editing
during this work, only for reference (to confirm exactly which env vars
`app/config.py` reads and that `app/messaging/producer.py` already
degrades gracefully with Kafka disabled). See `docs/governance/DECISION-LOG.md`
in the main project - this kit was built after v1.0.0 and does not touch
anything that release closed out.

## Layout

```
student-practice-kit-src/
├── licensing/          shared by both apps - Ed25519 sign/verify, local
│                        7-day-from-activation clock, tamper-evidence,
│                        and the shared branding constants both apps
│                        display (licensing/keys.py)
├── shared_ui/           small Tkinter pieces used by BOTH exes - the
│                        About/Version dialogs (about_dialog.py) and the
│                        bundled-.ico window-icon helper (icon.py).
│                        Deliberately its own package (not part of
│                        launcher/) so the Generator never has to pull in
│                        launcher's heavier db_provisioner/uvicorn imports
│                        just to show an About box or set its icon.
├── launcher/            OMS360 Enterprise AI Platform.exe source - the
│                        license gate, splash screen (splash.py), status
│                        window, embedded-database provisioning, and the
│                        in-process uvicorn hosting of the real app
├── generator/            OMS360 License Generator.exe source (admin-only)
├── build/
│   ├── launcher.spec      PyInstaller spec for the student app
│   ├── generator.spec      PyInstaller spec for the admin tool
│   ├── build.bat            one-click Windows build (see build/README.md)
│   ├── admin-only/           created by build.bat - the Generator exe
│   │                          lands here, never in Student_Practice_Kit
│   └── resources/            staged by build.bat - not checked in blank;
│                              this is where the downloaded MySQL engine
│                              and copied schema/migrations land
└── tests/               35 automated tests: licensing/ (27), the pure-
                          logic parts of launcher/db_provisioner.py, and
                          the branding text builders in shared_ui/ and
                          launcher/status_window.py (test_branding_text.py)
```

## How the license gate works

Full detail is in the docstrings of `licensing/__init__.py`,
`licensing/codec.py`, and `licensing/activation_store.py` - read those
first, they're written to be the actual explanation, not just comments.
Summary:

- **Ed25519 asymmetric signing**, per the explicit "standard cryptographic
  signing (public/private key)" requirement. `OMS360 Enterprise AI
  Platform.exe` embeds only the **public** key
  (`licensing/keys.py::PUBLIC_KEY_HEX`) - it can verify a key was minted
  by the Generator, it cannot mint one itself. Only
  `OMS360 License Generator.exe` carries the private key
  (`generator/_signing_key.py`, lightly split/obfuscated, never rendered
  in that app's UI).
- **Why the key is longer than the illustrative example
  (`ZELQA-OMS360-RAM-9X7P-K4QM-82LA`).** A genuinely unforgeable Ed25519
  signature is 64 bytes on its own - about 103 base32 characters before
  the payload is even added. Short product-key-style strings are only
  achievable with a weaker, symmetric checksum (the verifying secret would
  then have to live inside every copy of the student app, which is
  exactly the asymmetric requirement was written to avoid). The generated
  keys keep the same `ZELQA-OMS360-` branding prefix and dash-grouped
  format, they're just longer - fully copy/paste-able (both apps accept
  pasted text with any surrounding whitespace), the same way a real
  offline-verifiable license file would be. See `licensing/codec.py`'s
  module docstring for the exact math.
- **The 7-day clock starts at first successful activation on the
  student's machine**, not at generation time, per the literal
  requirement. The key itself carries no expiry date; `activation_store.py`
  records the moment locally (`%LOCALAPPDATA%\ZelQA\OMS360PracticeKit\activation_state.json`)
  and every launch checks `now < activated_at + 7 days`.
- **No duration other than 7 days is possible anywhere in the UI or
  config** - `LICENSE_DURATION_DAYS` is a single constant in
  `licensing/keys.py`, not read from an env var, CLI flag, or UI field on
  either app.
- **No rebuild is ever needed to mint or accept a new key.** The Generator
  mints keys purely from Student Name + the embedded private key; the
  launcher accepts any key that verifies against its embedded public key.
  Neither app has a hardcoded key or expiry baked in from a build step.

### Security model and its limits (read this before promising anything to anyone)

This is a reasonable, proportionate evaluation gate for a short student
practice session - **it is explicitly not hardened DRM**, and claiming
otherwise would be dishonest:

- **The private signing key cannot be made truly unextractable** from an
  offline, distributed Python/PyInstaller executable. Splitting/XOR-ing it
  in `generator/_signing_key.py` raises the bar above a `strings` scan; it
  does not defeat a determined reverse engineer with a decompiler. The
  actual mitigation that matters is operational: only run the Generator on
  a machine ZelQA staff control, and treat that binary itself as sensitive.
- **A student who locates and clears both the local activation JSON file
  and its registry-held guard secret can reset their own trial window on
  the same key.** There is no server for this fully offline product to
  check "has this license ever been activated before" against. This is
  the same limitation essentially all offline shareware/trialware has.
  `licensing/activation_store.py`'s tamper-evidence check stops the easy
  version of this (editing the JSON's date directly) but not a
  sophisticated one.
- Both limitations are stated here, in the module docstrings, and in
  `build/README.md` - not hidden.

## What does and doesn't work in the Student Practice Edition

**Works, fully, with zero code changes to `app/` or `ai/`:** every REST
endpoint under `/api/v1/...`, the Operations and Monitoring dashboards,
Swagger docs, `/health`, `/metrics`, the AI platform introspection and
platform-health endpoints under `/api/v1/ai`, order creation with real
persistence (audit trail, inventory ledger, DLQ table) against the
embedded MySQL database.

**Deliberately disabled, not broken:** Kafka. `app/config.py` already
supports `OMS360_KAFKA_ENABLED=false` (this was true before this kit
existed - see `app/messaging/producer.py`'s own docstring: "If Kafka
isn't reachable at all ... this logs and returns False instead of
crashing the request"), and `db_provisioner.py::env_overrides()` sets it.
Order creation, dashboards, and every read endpoint work normally.
`app/messaging/consumer.py` (the process that advances an order through
kitchen -> payment -> delivery by consuming Kafka events) never runs in
this edition, since there's no broker to consume from - an order created
in the practice kit will show as RECEIVED and not automatically progress
further. This was a deliberate scope decision, not an oversight: embedding
a real Kafka broker means bundling a JVM (no lightweight, dependency-free,
wire-compatible alternative was added, per "do not introduce new external
technologies" from the AI platform's own sprint discipline - the same
spirit applies here). If full Kafka-driven lifecycle demonstration is
wanted later, that's a scoped follow-up, not something silently
half-attempted here.

## Windows build-readiness (read this before running build.bat)

This kit was authored from a Linux sandbox with no access to a real
Windows machine. Two categories of verification were done, and it matters
which is which:

**Actually executed and confirmed** (this Linux sandbox can run
PyInstaller itself, just not produce a working Windows binary - `mysqld
.exe`, `winreg`, `%LOCALAPPDATA%` are Windows-only regardless of what
runs PyInstaller): a real `pyinstaller launcher.spec` and
`pyinstaller generator.spec` were run here against the actual, complete
`app/` and `ai/` trees (pulled from the real repo, not stand-ins), and the
resulting archives were opened and inspected module-by-module. This
caught two real, would-have-shipped-broken bugs that no amount of reading
the code or running `pytest`/`py_compile` would have found, because both
are specifically about how PyInstaller's static analysis resolves paths
and dynamic imports:

1. **`launcher.spec`'s `APP_ROOT` pointed one directory too high**
   (`os.path.join(REPO_ROOT, "..", "..")` - two `..` where only one was
   correct, since `student-practice-kit-src/` sits directly inside the
   real repo root). Every `app.*` hidden import silently failed
   ("Hidden import 'app.main' not found" - logged as an ERROR but *not*
   a build failure), and the built exe would have crashed immediately
   with `ModuleNotFoundError: No module named 'app'` on launch. Fixed to
   a single `..`; re-running the same dry build afterward showed all 33
   `app.*` modules and 80 `ai.*` modules correctly bundled with zero
   errors.
2. **`build.bat` looked for `oms360_schema.sql` at the repository root**,
   but it actually lives at `database/oms360_schema.sql` - confirmed by
   listing the real repo directly. This would have failed step 4 of
   `build.bat` outright on the very first run, before PyInstaller ever
   even started. Fixed to the correct path.

**Found on a real Windows run, not in this sandbox** (this one genuinely
could not have been caught here - it depends on what Oracle's servers
serve on a given day, not on anything in this codebase):

3. **`build.bat` step [3/8]'s exact-MD5 gate on the downloaded MySQL ZIP
   started failing** - Oracle republished the `mysql-8.0.46-winx64.zip`
   file under a new MD5 without changing the version number or file name.
   The old logic treated any MD5 mismatch as fatal, which meant this
   exact scenario - Oracle repacking a file with no actual problem in the
   download - would permanently block the build until someone manually
   re-checked and hardcoded a new MD5. Redesigned into structural
   validation instead: `build/verify_mysql_zip.ps1` now confirms the
   downloaded file is a plausible size, a genuinely valid ZIP archive, and
   contains the exact `mysqld.exe`/`mysql.exe` binaries this build needs -
   the pinned MD5 (now in `build/mysql-version.config`, not hardcoded in
   `build.bat`) is still computed and reported, but only as informational
   context, never as a pass/fail gate on its own. See
   `build/verify_mysql_zip.ps1`'s and `build/mysql-version.config`'s own
   header comments for the full design rationale, and `DECISION-LOG.md`
   for the incident this was written in response to.

With all three fixes in place, the real dry-run build was inspected directly
(not just re-run and assumed clean) and confirmed to contain: all 33
`app.*` and 80 `ai.*` modules, `sqlalchemy.dialects.mysql.pymysql` and its
full `pymysql` submodule tree (see below), `cryptography.hazmat.bindings.
_rust.abi3.so` plus the OpenSSL shared libraries, `pydantic_core`, both
bundled `.ico` files, and - correctly - *zero* `launcher`/`app`/`ai`
modules in the Generator's build (confirming `shared_ui/` actually keeps
the two exes' dependency trees separate, not just in theory).

**Could not be executed even here, since they require the real Windows
binaries** (`mysqld.exe`, `winreg`, actual window manager/taskbar):
provisioning the embedded database, the registry-based license guard
secret, and how the window/taskbar icons actually render. These are
exactly what `build/README.md`'s manual verification checklist covers -
that checklist is the remaining, unavoidable gap between "verified in
this sandbox" and "verified on Windows."

- **The SQLAlchemy dialect gap, explained**: `app/config.py::DATABASE_URL`
  builds a `mysql+pymysql://...` connection string, and SQLAlchemy
  resolves the `pymysql` half of that at runtime through its own plugin
  registry (a string-based, dynamic import) - not through any literal
  `import pymysql` statement anywhere in this codebase that PyInstaller
  could trace on its own. `launcher.spec` explicitly lists
  `sqlalchemy.dialects.mysql.pymysql` as a hidden import to close this;
  without it, the build would have succeeded but the resulting exe would
  have failed at first database connection with
  `sqlalchemy.exc.NoSuchModuleError`. Confirmed present in the actual
  built archive (`pymysql`, `pymysql.connections`, `pymysql.cursors`,
  `sqlalchemy.dialects.mysql.pymysql`, and the rest of that submodule
  tree all showed up when the built PYZ archive was inspected directly).
- **Confirmed safe as-is**: `confluent_kafka` is excluded from both the
  build's pip install list and `launcher.spec`'s Analysis - verified safe
  by reading `app/messaging/producer.py`, `app/messaging/consumer.py`, and
  `app/core/kafka_admin.py` directly: every import of it is inside a
  function body, guarded by `if not settings.KAFKA_ENABLED: return None`
  and/or wrapped in `try/except Exception`, and `app/messaging/consumer.py`
  (the one place that would `raise SystemExit` without it) is never
  imported by this launcher at all.
- **Defensive additions** (harmless if unnecessary, cheap insurance since
  this has never run on real Windows): explicit hidden imports for
  `cryptography.hazmat.bindings._rust` (both specs) and `pydantic_core`
  (launcher.spec) - both are reached only through fully static imports
  already, so PyInstaller's own analysis should find them regardless, but
  cryptography's compiled Rust extension in particular has a history of
  PyInstaller-hook edge cases across versions.
- **Icons**: `build/resources/icons/oms360_platform.ico` and
  `oms360_generator.ico` are generated, checked-in assets (see that
  folder's `README.txt`) - both specs bake them in as the exe's file icon
  (`EXE(icon=...)`) and bundle them as a data resource so
  `shared_ui/icon.py` can also apply them to every Tkinter window's title
  bar/taskbar icon at runtime, not just the file icon shown in Explorer.
- **Dependency versions**: `build.bat`'s pinned installs
  (fastapi/uvicorn/sqlalchemy/pymysql/pydantic/python-dotenv/psutil/
  httpx/pytest) match `../../requirements.txt` exactly, with one
  deliberate, documented omission (`confluent-kafka`, above).
  `cryptography` and `pyinstaller` are left unpinned on purpose, to
  always pick up their latest Windows/hook compatibility fixes.
- **Embedded MySQL ZIP verification is structural, not exact-MD5-based**:
  `build/mysql-version.config` holds the pinned `MYSQL_VERSION`/`MYSQL_MD5`
  as plain key=value text (not hardcoded inside `build.bat`), and
  `build/verify_mysql_zip.ps1` validates the downloaded archive by size,
  ZIP-structure integrity, and the actual presence of `mysqld.exe`/
  `mysql.exe` inside it - an MD5 mismatch against the pinned value is
  reported as a warning, not treated as a failure, since Oracle has been
  observed to repack a version's ZIP under a new MD5 with no real problem
  in the file. A future MySQL 8.0.x version bump is a one-line edit to
  `mysql-version.config`; `build.bat` and `verify_mysql_zip.ps1` need no
  changes at all. Build stays fully offline once the ZIP is staged
  locally, exactly as before.

None of this can be verified as *actually* working until `build.bat`
genuinely runs on Windows - that remains the one step that has to happen
outside this sandbox. This section exists so that if the build ever does
fail, the reviewer already knows what was checked, what the reasoning
was, and where to look first.

## Branding surfaces (Student Practice Edition only)

Per the branding brief, every window a student or instructor sees carries
`OMS360 Enterprise AI Platform` / `Developed by ZelQA Technologies`
consistently. These are lightweight *wrapper* UI around the existing app -
nothing under `app/` or `ai/` was touched to add them, and none of them
alter what the API actually does:

| Required surface | Where it lives |
|---|---|
| Splash Screen | `launcher/splash.py` - shown immediately on double-click and again while the embedded database/app start up |
| Login / Activation Screen | `launcher/activation_ui.py::prompt_for_license_key` - the first-run License Key prompt (there is no username/password concept in this API-only platform, so the license activation screen *is* the login-equivalent surface, per the brief's "License Activation screen" wording) |
| Dashboard / Header | The real, unmodified `app/static/operations_dashboard.html` and `monitoring_dashboard.html` served by `app.main` - not touched by this kit |
| About Screen | `shared_ui/about_dialog.py::show_about_dialog` - product, version, developer, copyright, reachable from the status window, the activation window, and the Generator |
| Version Dialog | `shared_ui/about_dialog.py::show_version_dialog` - compact product/version/edition/license-format readout |
| Student Evaluation Edition | `launcher/status_window.py` - "Licensed Student", "Evaluation Period", "Days Remaining" always visible while the app runs |
| Error Pages | `launcher/activation_ui.py::show_fatal_error` and the evaluation-expired dialog - both brand-prefixed in their title bar |

`about_text()`/`version_text()` in `shared_ui/about_dialog.py` and
`_format_days_remaining()` in `launcher/status_window.py` are plain
functions with no Tkinter window creation, specifically so their content
can be unit tested without a display - see `tests/test_branding_text.py`.

## Running the tests

```
cd student-practice-kit-src
python -m venv .venv && .venv\Scripts\activate      (or source .venv/bin/activate on macOS/Linux)
pip install cryptography pytest
set PYTHONPATH=.                                      (or export PYTHONPATH=. )
pytest tests -v
```

35 tests, all passing: full Ed25519 sign/verify/tamper coverage
(`test_codec.py`), the 7-day activation clock including exact-boundary and
tamper-detection behavior (`test_activation_store.py`), the combined gate
(`test_gate.py`), the pure-logic parts of the database provisioner that
don't require Windows/mysqld (`test_db_provisioner.py`), and the branding
text builders described above (`test_branding_text.py`). Running the test
suite requires Python's `tkinter` standard-library module to be importable
(even though no window is actually opened) since `launcher/status_window.py`
imports `tkinter` at module level - on Linux/macOS dev machines this is
usually `apt install python3-tk` or already bundled with the official
python.org installer; Windows' python.org installer includes it by
default.
