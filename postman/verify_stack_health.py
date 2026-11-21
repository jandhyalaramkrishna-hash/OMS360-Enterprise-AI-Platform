#!/usr/bin/env python3
"""
OMS-360 Enterprise QA - Application/Stack Health Verification.

Shared engine used by BOTH Run_QA_Pipeline.bat and jenkins/Jenkinsfile,
called BEFORE any test executes, so local and CI runs follow the identical
execution flow.

Verifies four things and reports each individually:
  1. Docker containers - via `docker compose ps` (every service's State/Health)
  2. Kafka broker       - via GET {base_url}/health -> dependencies.kafka_broker
  3. MySQL               - via GET {base_url}/health -> dependencies.database
  4. FastAPI              - the /health call itself succeeding is proof
                             FastAPI is up and responding

This script NEVER starts Docker Desktop, `docker compose up`, or the
application in any way - verification only. If the stack is not already
running (started separately via START_OMS360.bat), this fails immediately
with the exact required message - it does not wait around for a startup
that was never triggered.

Exit code 0 = all four verified healthy. Exit code 1 = at least one failed.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request

REQUIRED_FAILURE_MESSAGE = (
    "Application is not running. Execute START_OMS360.bat and verify all "
    "services before running the QA pipeline."
)


def check_docker_containers():
    try:
        out = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, timeout=15,
        )
    except FileNotFoundError:
        return False, "docker / docker compose not found on PATH"
    except Exception as exc:
        return False, f"could not run 'docker compose ps' ({exc})"

    if out.returncode != 0:
        return False, f"'docker compose ps' failed: {(out.stderr or out.stdout).strip()[:200]}"

    text = (out.stdout or "").strip()
    if not text:
        return False, "no containers found - the stack is not up"

    # `docker compose ps --format json` emits either one JSON array or NDJSON
    # (one object per line) depending on the installed Compose version -
    # handle both rather than assuming one.
    services = []
    try:
        parsed = json.loads(text)
        services = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                services.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not services:
        return False, "could not parse 'docker compose ps' output"

    bad = []
    for svc in services:
        name = svc.get("Service") or svc.get("Name") or "unknown"
        state = (svc.get("State") or "").lower()
        health = (svc.get("Health") or "").lower()
        if state != "running":
            bad.append(f"{name} (state={state or 'unknown'})")
        elif health and health != "healthy":
            bad.append(f"{name} (health={health})")

    if bad:
        return False, "unhealthy/stopped container(s): " + ", ".join(bad)
    return True, f"{len(services)} container(s) running and healthy"


def check_app_health(base_url, timeout=5.0):
    url = f"{base_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return None, False, f"HTTP {resp.status} from {url}"
            body = json.loads(resp.read().decode("utf-8"))
            return body, True, None
    except Exception as exc:
        return None, False, f"could not reach {url} ({exc})"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument(
        "--retries", type=int, default=2,
        help="Quick re-checks to smooth over a single transient network blip - "
             "NOT a startup-wait loop. Default: 2 (a few seconds total).",
    )
    parser.add_argument("--retry-delay", type=float, default=2.0)
    args = parser.parse_args()

    print("=" * 79)
    print(" OMS-360 QA Pipeline - Application/Stack Health Verification")
    print(" (read-only checks - this script never starts Docker or the app)")
    print("=" * 79)

    docker_ok, docker_msg = check_docker_containers()

    body, fastapi_ok, err = None, False, None
    for attempt in range(args.retries + 1):
        body, fastapi_ok, err = check_app_health(args.base_url)
        if fastapi_ok:
            break
        if attempt < args.retries:
            time.sleep(args.retry_delay)

    print(f"  [{'OK' if fastapi_ok else 'FAIL'}] FastAPI /health   : "
          f"{'responded' if fastapi_ok else err}")

    kafka_ok = False
    mysql_ok = False
    if fastapi_ok and body:
        deps = body.get("dependencies", {})
        kafka_status = str(deps.get("kafka_broker", "")).upper()
        db_status = str(deps.get("database", "")).upper()
        kafka_ok = kafka_status.startswith("UP") or kafka_status == "DISABLED"
        mysql_ok = db_status.startswith("UP")
        print(f"  [{'OK' if kafka_ok else 'FAIL'}] Kafka broker      : {deps.get('kafka_broker', 'unknown')}")
        print(f"  [{'OK' if mysql_ok else 'FAIL'}] MySQL             : {deps.get('database', 'unknown')}")
        print(f"       Overall application status: {body.get('status', 'unknown')}")
    else:
        print("  [FAIL] Kafka broker      : could not check - FastAPI unreachable")
        print("  [FAIL] MySQL             : could not check - FastAPI unreachable")

    # Native (no-Docker) run: the app itself reports docker=NOT_CONTAINERIZED,
    # so a missing `docker compose` stack is expected, not a failure.
    if (not docker_ok and fastapi_ok and body
            and str(body.get("dependencies", {}).get("docker", "")).upper() == "NOT_CONTAINERIZED"):
        docker_ok, docker_msg = True, "not used - app reports NOT_CONTAINERIZED (native run)"
    print(f"  [{'OK' if docker_ok else 'FAIL'}] Docker containers : {docker_msg}")

    all_ok = docker_ok and fastapi_ok and kafka_ok and mysql_ok
    print("=" * 79)
    if all_ok:
        print(" RESULT: Stack is healthy - proceeding.")
        print("=" * 79)
        sys.exit(0)
    else:
        print(f" RESULT: {REQUIRED_FAILURE_MESSAGE}")
        print("=" * 79)
        sys.exit(1)


if __name__ == "__main__":
    main()
