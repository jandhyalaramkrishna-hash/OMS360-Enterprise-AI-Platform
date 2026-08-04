"""
Tests for licensing/activation_store.py - the local 7-day-from-first-
activation clock and its tamper-evidence check.

These tests force the non-Windows (file-based guard secret) code path by
running in this Linux test environment - `platform.system() != "Windows"`
is true here, so `_get_or_create_guard_secret` uses the file fallback.
The Windows registry path (`_get_or_create_guard_secret_registry`) is
exercised only on an actual Windows machine; its logic is a thin,
directly-analogous wrapper around the same `winreg.SetValueEx` /
`QueryValueEx` calls already covered by Python's own stdlib tests, so it
is deliberately not re-tested here with a registry mock - see README.md's
"What is and isn't tested here" section.
"""

import json

import pytest

from licensing import keys
from licensing.activation_store import ActivationStore


@pytest.fixture
def store(tmp_path):
    return ActivationStore(state_dir=tmp_path)


def test_fresh_install_reports_not_activated(store):
    status = store.read_status()
    assert status.activated is False
    assert status.expired is False


def test_record_activation_marks_activated_and_not_expired(store):
    status = store.record_activation("RAM", "deadbeef", "ZELQA-OMS360-XXXXX")
    assert status.activated is True
    assert status.expired is False
    assert status.student_tag == "RAM"
    assert status.license_id_hex == "deadbeef"
    assert status.seconds_remaining > 0


def test_activation_persists_across_a_new_store_instance(tmp_path):
    store1 = ActivationStore(state_dir=tmp_path)
    store1.record_activation("RAM", "deadbeef", "ZELQA-OMS360-XXXXX")

    store2 = ActivationStore(state_dir=tmp_path)  # simulates the next launch
    status = store2.read_status()
    assert status.activated is True
    assert status.student_tag == "RAM"


def test_activating_twice_does_not_reset_the_clock(store, monkeypatch):
    import time as time_module

    t0 = 1_000_000_000
    monkeypatch.setattr(time_module, "time", lambda: t0)
    first = store.record_activation("RAM", "deadbeef", "ZELQA-OMS360-KEY1")
    assert first.activated_at_unix == t0

    # "Re-enter" a key (same or different) 3 days later - must NOT push
    # activated_at forward.
    monkeypatch.setattr(time_module, "time", lambda: t0 + 3 * 86400)
    second = store.record_activation("RAM", "deadbeef", "ZELQA-OMS360-KEY1")
    assert second.activated_at_unix == t0


def test_expires_after_exactly_seven_days(tmp_path, monkeypatch):
    import time as time_module

    t0 = 1_000_000_000
    monkeypatch.setattr(time_module, "time", lambda: t0)
    store = ActivationStore(state_dir=tmp_path)
    store.record_activation("RAM", "deadbeef", "ZELQA-OMS360-KEY1")

    # One second before the boundary: still valid.
    monkeypatch.setattr(
        time_module, "time",
        lambda: t0 + keys.LICENSE_DURATION_DAYS * 86400 - 1,
    )
    assert store.read_status().expired is False

    # One second after the boundary: expired.
    monkeypatch.setattr(
        time_module, "time",
        lambda: t0 + keys.LICENSE_DURATION_DAYS * 86400 + 1,
    )
    assert store.read_status().expired is True


def test_editing_the_json_file_directly_is_detected_as_corrupt(store):
    store.record_activation("RAM", "deadbeef", "ZELQA-OMS360-KEY1")

    # Simulate a student trying to "reset the trial" by hand-editing the
    # activation timestamp in the JSON file to push expiry into the future.
    record = json.loads(store.state_path.read_text())
    record["activated_at_unix"] = 9_999_999_999  # far future
    store.state_path.write_text(json.dumps(record))

    status = store.read_status()
    assert status.corrupt is True
    assert status.expired is True  # fail closed, not "not yet activated"


def test_deleting_the_state_file_looks_like_a_fresh_install(store):
    """Documents a known, explicitly-accepted limitation (see this
    module's docstring and README.md): deleting BOTH the JSON file and
    the guard secret resets the local trial. This test exists so that
    behavior is a deliberate, observed fact - not a silent surprise."""
    store.record_activation("RAM", "deadbeef", "ZELQA-OMS360-KEY1")
    store.state_path.unlink()
    guard_path = store.state_dir / ".guard"
    guard_path.unlink()

    status = store.read_status()
    assert status.activated is False
