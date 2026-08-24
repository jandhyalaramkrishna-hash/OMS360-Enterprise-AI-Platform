#!/usr/bin/env python3
"""
OMS-360 Enterprise QA - Allure report integrity verification.

Run by Generate_Allure_Report.bat (and, for defense-in-depth, by
jenkins/Jenkinsfile) immediately AFTER `allure generate` reports a zero
exit code. A zero exit code from `allure generate` only means the CLI
didn't crash - it does NOT guarantee the output actually contains real
data behind every tab. This script answers that question honestly by
checking, on disk, for the specific files each Allure report tab reads
at runtime:

  1. Raw results       allure-results/*-result.json   (Overview/Suites/Behaviors/Timeline source data)
  2. Enterprise meta    allure-results/environment.properties, executor.json, categories.json
  3. History input      allure-results/history/  (informational only - absent on first-ever run)
  4. Generated output   allure-report/index.html, data/*.json, widgets/*.json, history/history.json

It does NOT re-run `allure generate` and does NOT modify FastAPI,
Docker, Kafka, or any application code - read-only verification of the
QA report artifacts only.

Exit code 0  = report looks structurally sound (or only the expected
               first-run "no history yet" note was printed).
Exit code 1  = at least one real problem found - printed explicitly,
               so the caller can stop and show the user the exact cause
               instead of silently declaring success.
"""
import argparse
import json
import sys
from pathlib import Path

FAILURES = []
WARNINGS = []


def fail(msg):
    FAILURES.append(msg)
    print(f"  [FAIL] {msg}")


def ok(msg):
    print(f"  [OK] {msg}")


def warn(msg):
    WARNINGS.append(msg)
    print(f"  [WARN] {msg}")


def check_raw_results(results_dir: Path):
    print("\nStep 1/4: Raw Allure result files (allure-results/*-result.json)")
    result_files = sorted(results_dir.glob("*-result.json"))
    if not result_files:
        fail(f"No *-result.json files found in {results_dir} - "
             f"Newman (--reporter-allure-resultsDir) and/or pytest "
             f"(--alluredir) did not write any raw results here.")
        return
    invalid = []
    for f in result_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "uuid" not in data or "status" not in data:
                invalid.append((f.name, "missing required 'uuid'/'status' keys"))
        except Exception as exc:
            invalid.append((f.name, str(exc)))
    if invalid:
        fail(f"{len(invalid)} of {len(result_files)} result file(s) are invalid:")
        for name, reason in invalid[:10]:
            print(f"         - {name}: {reason}")
    else:
        ok(f"{len(result_files)} result file(s) found, all valid JSON with required fields.")


def check_metadata_files(results_dir: Path):
    print("\nStep 2/4: Enterprise metadata files (environment.properties / executor.json / categories.json)")
    env_file = results_dir / "environment.properties"
    if not env_file.exists() or env_file.stat().st_size == 0:
        fail(f"{env_file} is missing or empty.")
    else:
        ok(f"environment.properties present ({env_file.stat().st_size} bytes).")

    for name in ("executor.json", "categories.json"):
        f = results_dir / name
        if not f.exists():
            fail(f"{f} is missing.")
            continue
        try:
            json.loads(f.read_text(encoding="utf-8"))
            ok(f"{name} present and valid JSON ({f.stat().st_size} bytes).")
        except Exception as exc:
            fail(f"{f} exists but is not valid JSON: {exc}")


def check_history_input(results_dir: Path):
    print("\nStep 3/4: History input (allure-results/history/ - carried forward for Trend/Timeline)")
    history_dir = results_dir / "history"
    if not history_dir.exists():
        warn("No allure-results/history/ found - expected on the very first run "
             "(nothing to carry forward yet). The Trend graph appears from the 2nd run onward.")
    else:
        files = list(history_dir.glob("*.json"))
        if files:
            ok(f"history/ present with {len(files)} file(s) - trend data carried forward.")
        else:
            warn("history/ folder exists but is empty.")


def check_report_output(report_dir: Path):
    print("\nStep 4/4: Generated report output (allure-report/)")
    required = [
        "index.html",
        "data/suites.json",
        "data/behaviors.json",
        "data/timeline.json",
        "widgets/categories.json",
        "widgets/environment.json",
        "widgets/executors.json",
    ]
    if not report_dir.exists():
        fail(f"{report_dir} does not exist - `allure generate` did not produce output here.")
        return
    for rel in required:
        f = report_dir / rel
        if not f.exists():
            fail(f"{f} is missing.")
        elif f.stat().st_size == 0:
            fail(f"{f} exists but is empty (0 bytes).")
        else:
            ok(f"{rel} present ({f.stat().st_size} bytes).")

    history_json = report_dir / "history" / "history.json"
    if history_json.exists() and history_json.stat().st_size > 0:
        ok(f"history/history.json present ({history_json.stat().st_size} bytes) - Trend graph will render.")
    else:
        warn("history/history.json missing or empty - Trend graph will be blank until the next run.")


def main():
    parser = argparse.ArgumentParser(description="Verify Allure report integrity (read-only).")
    parser.add_argument("--allure-results-dir", default="allure-results")
    parser.add_argument("--allure-report-dir", default="allure-report")
    args = parser.parse_args()

    results_dir = Path(args.allure_results_dir)
    report_dir = Path(args.allure_report_dir)

    print("=" * 79)
    print(" OMS-360 Enterprise QA - Allure Report Integrity Verification")
    print("=" * 79)

    check_raw_results(results_dir)
    check_metadata_files(results_dir)
    check_history_input(results_dir)
    check_report_output(report_dir)

    print()
    print("=" * 79)
    if FAILURES:
        print(f" RESULT: FAILED - {len(FAILURES)} problem(s) found (see [FAIL] lines above)")
        print("=" * 79)
        sys.exit(1)

    print(" RESULT: Allure report structure looks sound.")
    if WARNINGS:
        print(f" ({len(WARNINGS)} informational warning(s) above - see [WARN] lines)")
    print("=" * 79)
    print()
    print(" IMPORTANT - how to open the report:")
    print("   Run:  allure open allure-report")
    print()
    print("   Do NOT double-click allure-report\\index.html directly, and do not")
    print("   open it via a plain 'start' on the file path. Browsers block the")
    print("   report's own JavaScript from fetching its data/*.json files under")
    print("   the file:// protocol (CORS), which shows as a blank page or")
    print("   '500 Failed to fetch' even though the report itself generated")
    print("   correctly. `allure open` serves the exact same files over a real")
    print("   local HTTP server, which is the standard, supported way to view")
    print("   any Allure report.")
    print("=" * 79)
    sys.exit(0)


if __name__ == "__main__":
    main()
