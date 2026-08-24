#!/usr/bin/env python3
"""
OMS-360 Enterprise QA - Allure enterprise metadata generator.

Writes three files into allure-results/ so `allure generate` produces an
Enterprise-grade report with a populated Environment widget, Executor
widget, and custom failure Categories - on top of the History/Trend/
Timeline/Suites/Packages/Behaviors/Retries/Summary/Statistics views Allure
already builds automatically from the raw results:

  - environment.properties   (Environment tab)
  - executor.json            (Executor info shown on the Overview tab)
  - categories.json          (Categories tab - custom failure grouping)

Best-effort only: every external probe (HTTP call to the running app,
`node -v`, `newman -v`, `allure --version`) is wrapped so a failure here
never breaks the pipeline - metadata is a nice-to-have, not a test result.

Run from the repo root (or pass --allure-results-dir explicitly):
    python postman/generate_allure_metadata.py

Does not touch app/, ai/, docker/, docker-compose.yml, kafka/, playwright/,
or any application code - reporting metadata only.
"""
import argparse
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def _safe_run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return (out.stdout or out.stderr or "").strip()
    except Exception:
        return "unknown"


def _safe_http_get_json(url, timeout=2.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def write_environment_properties(allure_results_dir: Path, base_url: str):
    """.properties format: key = value, one per line (Allure's Environment tab)."""
    app_info = _safe_http_get_json(f"{base_url}/version")
    health_info = _safe_http_get_json(f"{base_url}/health")

    lines = [
        f"Application = OMS-360 Enterprise Order Management Engine",
        f"Application_Version = {(app_info or {}).get('version', 'unreachable')}",
        f"Application_Build = {(app_info or {}).get('build_version', 'unreachable')}",
        f"Application_Environment = {(app_info or {}).get('environment', 'unreachable')}",
        f"Application_Overall_Status = {(health_info or {}).get('status', 'unreachable')}",
        f"Base_URL = {base_url}",
        f"OS = {platform.platform()}",
        f"Python_Version = {platform.python_version()}",
        f"Node_Version = {_safe_run(['node', '-v'])}",
        f"Newman_Version = {_safe_run(['newman', '-v'])}",
        f"Allure_CLI_Version = {_safe_run(['allure', '--version'])}",
        f"Run_Timestamp_UTC = {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"Triggered_By = {os.environ.get('BUILD_URL', 'Local Execution')}",
    ]
    out_path = allure_results_dir / "environment.properties"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def write_executor_json(allure_results_dir: Path):
    """Populated by CI env vars when present (Jenkins), sensible local
    defaults otherwise. See https://allurereport.org/docs/how-it-works-executor-file/"""
    build_number = os.environ.get("BUILD_NUMBER")
    is_jenkins = bool(os.environ.get("JENKINS_URL"))

    executor = {
        "name": "Jenkins" if is_jenkins else "Local Execution",
        "type": "jenkins" if is_jenkins else "local",
        "reportName": "OMS-360 Enterprise QA Report",
        "buildName": os.environ.get("JOB_NAME", "OMS-360-QA-Local"),
        "buildOrder": int(build_number) if build_number and build_number.isdigit() else int(time.time()),
        "buildUrl": os.environ.get("BUILD_URL", ""),
        "reportUrl": os.environ.get("BUILD_URL", "") + "allure" if is_jenkins else "",
    }
    out_path = allure_results_dir / "executor.json"
    out_path.write_text(json.dumps(executor, indent=2), encoding="utf-8")
    return out_path


def write_categories_json(allure_results_dir: Path):
    """Custom failure categories. Grounded in the project's real error taxonomy
    (app/core/exceptions.py's OMSBusinessError subclasses / error_code values,
    and the real infrastructure dependencies in docker-compose.yml - MySQL,
    Kafka) plus the standard Product-defect vs Test-defect vs Infrastructure
    split. Not test-file-specific - matches on failure message/trace text,
    so it works without adding @allure decorators to any existing test."""
    categories = [
        {
            "name": "Business Rule Violations (expected 4xx)",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*(duplicate_order|inventory_lock_error|inventory_not_found|unknown_item|order_not_found|payment_failed|validation_error).*",
        },
        {
            "name": "Infrastructure - Database Unreachable",
            "matchedStatuses": ["broken", "failed"],
            "messageRegex": ".*(database_connection_error|Connection refused|Can't connect to MySQL|OperationalError).*",
        },
        {
            "name": "Infrastructure - Kafka Unreachable",
            "matchedStatuses": ["broken", "failed"],
            "messageRegex": ".*(kafka_publish_error|kafka_consume_error|broker_reachable.*false|KafkaException).*",
        },
        {
            "name": "API Contract Failures (unexpected status/shape)",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*(AssertionError|expected.*to have status|expected.*to be an array).*",
        },
        {
            "name": "Timeouts",
            "matchedStatuses": ["broken", "failed"],
            "messageRegex": ".*(timed out|ETIMEDOUT|ReadTimeout|TimeoutError).*",
        },
        {
            "name": "Unhandled / Internal Errors (real defects)",
            "matchedStatuses": ["broken", "failed"],
            "messageRegex": ".*(internal_error|500 Internal Server Error|Traceback).*",
        },
        {
            "name": "Test Defects (fixture/setup issues)",
            "matchedStatuses": ["broken"],
            "messageRegex": ".*(FixtureError|fixture.*not found|ImportError|ModuleNotFoundError).*",
        },
    ]
    out_path = allure_results_dir / "categories.json"
    out_path.write_text(json.dumps(categories, indent=2), encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allure-results-dir", default="allure-results",
                         help="Path to the allure-results directory (default: allure-results, relative to cwd).")
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://localhost:8000"),
                         help="Base URL of the running OMS-360 app, for environment.properties (default: http://localhost:8000).")
    args = parser.parse_args()

    allure_results_dir = Path(args.allure_results_dir)
    allure_results_dir.mkdir(parents=True, exist_ok=True)

    written = []
    try:
        written.append(write_environment_properties(allure_results_dir, args.base_url))
    except Exception as exc:
        print(f"[WARN] Could not write environment.properties: {exc}", file=sys.stderr)
    try:
        written.append(write_executor_json(allure_results_dir))
    except Exception as exc:
        print(f"[WARN] Could not write executor.json: {exc}", file=sys.stderr)
    try:
        written.append(write_categories_json(allure_results_dir))
    except Exception as exc:
        print(f"[WARN] Could not write categories.json: {exc}", file=sys.stderr)

    for p in written:
        print(f"[OK] Wrote {p}")

    if len(written) < 3:
        print("[WARN] One or more metadata files failed to write - continuing anyway (non-fatal).", file=sys.stderr)


if __name__ == "__main__":
    main()
