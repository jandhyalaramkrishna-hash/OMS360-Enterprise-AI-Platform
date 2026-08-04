"""Tests for licensing/gate.py - the combined codec + activation_store
entry point the launcher actually calls."""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from licensing import codec
from licensing.activation_store import ActivationStore
from licensing.errors import InvalidLicenseSignatureError
from licensing.gate import LicenseGate

_TEST_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(
    "5120fb00fa7f863dda5cfebeaa27ad055195c53ee20742dadc23754a6e3acf79"
))


@pytest.fixture
def gate(tmp_path):
    return LicenseGate(store=ActivationStore(state_dir=tmp_path))


def test_status_before_any_activation(gate):
    assert gate.current_status().activated is False


def test_activate_with_a_genuinely_issued_key_succeeds(gate, monkeypatch):
    # Use the real embedded public key path by issuing with the matching
    # test private key and monkeypatching codec's public key lookup to
    # match it (keeps this test independent of the production keypair
    # committed in licensing/keys.py, same as test_codec.py's approach).
    from licensing import keys as keys_module

    real_public_hex = _TEST_PRIVATE_KEY.public_key().public_bytes(
        encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.Raw,
        format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]).PublicFormat.Raw,
    ).hex()
    monkeypatch.setattr(keys_module, "PUBLIC_KEY_HEX", real_public_hex)

    key = codec.issue_license("RAM", _TEST_PRIVATE_KEY)
    status = gate.activate_with_key(key)
    assert status.activated is True
    assert status.student_tag == "RAM"
    assert status.expired is False


def test_activate_with_a_forged_key_raises_and_does_not_activate(gate):
    attacker_key = Ed25519PrivateKey.generate()
    forged = codec.issue_license("ATTACKER", attacker_key)

    with pytest.raises(InvalidLicenseSignatureError):
        gate.activate_with_key(forged)

    # Must not have side-effected an activation record.
    assert gate.current_status().activated is False
