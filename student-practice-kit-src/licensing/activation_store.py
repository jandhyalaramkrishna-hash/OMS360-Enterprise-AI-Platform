"""
licensing/activation_store.py - local, per-machine record of "when did
this copy first successfully activate", with a lightweight tamper-evidence
check.

Requirement being implemented: "Validity is always exactly 7 days from
first successful activation." The license key itself carries no expiry
date (see codec.py's docstring) - the clock is local, starts the first
time `record_activation()` is called, and every later launch just checks
`now < activated_at + LICENSE_DURATION_DAYS`.

Tamper-evidence design (read this before assuming it's unbreakable - it
isn't, and the module docstring in licensing/__init__.py says so too):

The activation record is a small JSON file. A naive "sign the JSON with a
key that's also stored in the same JSON" scheme provides no real
protection - anyone editing the file can see the key sitting right next
to the data it supposedly protects, and just recompute a valid signature
themselves. Instead:

  - A random 32-byte "guard secret" is generated once, on first ever run,
    and stored SEPARATELY from the activation JSON: in the Windows
    registry (HKCU\\Software\\ZelQA\\OMS360PracticeKit) rather than beside
    it. On non-Windows platforms (only relevant for development/testing -
    the shipped product is Windows-only per spec) it falls back to a
    second file next to, but distinct from, the activation record.
  - The activation JSON's HMAC-SHA256 is computed using that guard secret
    as the key. A student editing just the JSON (the obvious, easy-to-find
    file) will not have the registry-held secret, so their edited MAC
    will not match - the record is then treated as CORRUPT, which this
    module treats as EXPIRED (fail closed), not as "not yet activated".
    Treating corruption as "not yet activated" would hand back a fresh
    7 days to anyone willing to corrupt the file, which defeats the whole
    point.
  - This is a proportionate speed bump for a short student evaluation
    tool, not hardened DRM. Someone who finds and clears both the JSON
    file and the registry guard secret can still reset their local trial
    window on the same key - there is no server to prevent that for a
    fully offline product. This is the same limitation essentially all
    offline trial/shareware software has; it is stated here rather than
    quietly hoped nobody notices.
"""

import hashlib
import hmac
import json
import os
import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from licensing import keys
from licensing.errors import ActivationStateCorruptError

_APP_DATA_DIRNAME = "ZelQA"
_APP_SUBDIRNAME = "OMS360PracticeKit"
_STATE_FILENAME = "activation_state.json"
_GUARD_FILENAME = ".guard"  # non-Windows fallback only
_REGISTRY_PATH = r"Software\ZelQA\OMS360PracticeKit"
_REGISTRY_VALUE = "guard"


def default_state_dir() -> Path:
    """Where the activation record lives. %LOCALAPPDATA% on Windows (the
    conventional per-user, non-roaming location for this kind of local
    app state), falling back to a home-directory dotfolder elsewhere so
    the module is testable on non-Windows dev machines."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / ".local" / "share"
    return base / _APP_DATA_DIRNAME / _APP_SUBDIRNAME


def _get_or_create_guard_secret(state_dir: Path) -> bytes:
        return _get_or_create_guard_secret_file(state_dir)


def _get_or_create_guard_secret_registry() -> bytes:
    import winreg  # Windows-only stdlib module

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _REGISTRY_PATH) as key:
        try:
            value, _ = winreg.QueryValueEx(key, _REGISTRY_VALUE)
            secret = bytes.fromhex(value)
            if len(secret) == 32:
                return secret
        except FileNotFoundError:
            pass
        secret = os.urandom(32)
        winreg.SetValueEx(key, _REGISTRY_VALUE, 0, winreg.REG_SZ, secret.hex())
        return secret


def _get_or_create_guard_secret_file(state_dir: Path) -> bytes:
    guard_path = state_dir / _GUARD_FILENAME
    if guard_path.exists():
        data = guard_path.read_bytes()
        if len(data) == 32:
            return data
    state_dir.mkdir(parents=True, exist_ok=True)
    secret = os.urandom(32)
    guard_path.write_bytes(secret)
    return secret


def _compute_mac(guard_secret: bytes, record: dict) -> str:
    # Canonical, deterministic serialization of everything except the mac
    # field itself, so the mac covers the full record contents.
    payload = {k: v for k, v in record.items() if k != "mac"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(guard_secret, canonical, hashlib.sha256).hexdigest()


@dataclass
class ActivationStatus:
    activated: bool
    student_tag: Optional[str] = None
    license_id_hex: Optional[str] = None
    activated_at_unix: Optional[int] = None
    expires_at_unix: Optional[int] = None
    seconds_remaining: Optional[float] = None
    expired: bool = False
    corrupt: bool = False


class ActivationStore:
    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or default_state_dir()
        self.state_path = self.state_dir / _STATE_FILENAME

    def read_status(self) -> ActivationStatus:
        if not self.state_path.exists():
            return ActivationStatus(activated=False)

        try:
            record = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ActivationStatus(activated=False, corrupt=True, expired=True)

        guard_secret = _get_or_create_guard_secret(self.state_dir)
        expected_mac = _compute_mac(guard_secret, record)
        actual_mac = record.get("mac", "")
        if not hmac.compare_digest(expected_mac, actual_mac):
            # Tamper detected (or the guard secret was reset/lost) - fail
            # closed rather than silently granting a fresh window.
            return ActivationStatus(activated=True, corrupt=True, expired=True)

        activated_at = int(record["activated_at_unix"])
        expires_at = activated_at + keys.LICENSE_DURATION_DAYS * 86400
        now = int(time.time())
        remaining = expires_at - now

        return ActivationStatus(
            activated=True,
            student_tag=record.get("student_tag"),
            license_id_hex=record.get("license_id_hex"),
            activated_at_unix=activated_at,
            expires_at_unix=expires_at,
            seconds_remaining=max(0, remaining),
            expired=remaining <= 0,
            corrupt=False,
        )

    def record_activation(self, student_tag: str, license_id_hex: str, raw_key: str) -> ActivationStatus:
        """Called exactly once - the moment a license key first verifies
        successfully. If a (non-corrupt, non-expired) activation already
        exists, this is a no-op that just returns the existing status,
        so re-entering the same key twice never resets the clock."""
        existing = self.read_status()
        if existing.activated and not existing.corrupt:
            return existing

        self.state_dir.mkdir(parents=True, exist_ok=True)
        guard_secret = _get_or_create_guard_secret(self.state_dir)

        now = int(time.time())
        record = {
            "student_tag": student_tag,
            "license_id_hex": license_id_hex,
            "raw_key_sha256": hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
            "activated_at_unix": now,
        }
        record["mac"] = _compute_mac(guard_secret, record)
        self.state_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

        return self.read_status()
