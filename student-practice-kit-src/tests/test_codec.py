"""
Tests for licensing/codec.py - Ed25519 signing/verification and the pretty
key encoding. Plain functions + assertions run via pytest (no unittest
boilerplate), matching the OMS360 AI platform's own test style.
"""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from licensing import codec
from licensing.errors import InvalidLicenseFormatError, InvalidLicenseSignatureError


@pytest.fixture
def real_private_key():
    # A fixed, known-good test key (NOT the production key embedded in
    # licensing/keys.py) so these tests are self-contained and don't
    # depend on the shipped keypair.
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(
        "5120fb00fa7f863dda5cfebeaa27ad055195c53ee20742dadc23754a6e3acf79"
    ))


@pytest.fixture
def real_public_key(real_private_key):
    return real_private_key.public_key()


def test_issued_key_has_expected_prefix_and_is_uppercase(real_private_key):
    key = codec.issue_license("Ram", real_private_key)
    assert key.startswith("ZELQA-OMS360-")
    assert key == key.upper()


def test_two_generations_for_same_student_are_unique(real_private_key):
    key1 = codec.issue_license("RAM", real_private_key)
    key2 = codec.issue_license("RAM", real_private_key)
    assert key1 != key2


def test_valid_key_round_trips_student_name(real_private_key, real_public_key):
    key = codec.issue_license("Priya", real_private_key)
    payload = codec.verify_license(key, public_key=real_public_key)
    assert payload.student_tag == "Priya"
    assert len(payload.license_id) == 4
    assert payload.issued_at_unix > 0


def test_key_accepts_paste_with_surrounding_whitespace_and_newlines(real_private_key, real_public_key):
    key = codec.issue_license("RAM", real_private_key)
    pasted = f"  \n{key}\n  "
    payload = codec.verify_license(pasted, public_key=real_public_key)
    assert payload.student_tag == "RAM"


def test_key_is_case_insensitive_on_input(real_private_key, real_public_key):
    key = codec.issue_license("RAM", real_private_key)
    payload = codec.verify_license(key.lower(), public_key=real_public_key)
    assert payload.student_tag == "RAM"


def test_forged_key_from_a_different_private_key_is_rejected(real_public_key):
    attacker_key = Ed25519PrivateKey.generate()
    forged = codec.issue_license("ATTACKER", attacker_key)
    with pytest.raises(InvalidLicenseSignatureError):
        codec.verify_license(forged, public_key=real_public_key)


def test_tampering_with_the_payload_or_signature_is_rejected(real_private_key, real_public_key):
    key = codec.issue_license("RAM", real_private_key)
    # Flip a character well inside the encoded body (not the last
    # character - see the note below on why the trailing character is a
    # special case).
    mid = len(key) // 2
    ch = key[mid]
    tampered = key[:mid] + ("A" if ch != "A" else "B") + key[mid + 1:]
    with pytest.raises(InvalidLicenseSignatureError):
        codec.verify_license(tampered, public_key=real_public_key)


def test_wrong_prefix_is_rejected(real_public_key):
    with pytest.raises(InvalidLicenseFormatError):
        codec.verify_license("NOTZELQA-SOMETHING", public_key=real_public_key)


def test_empty_string_is_rejected(real_public_key):
    with pytest.raises(InvalidLicenseFormatError):
        codec.verify_license("", public_key=real_public_key)


def test_almost_every_single_character_change_breaks_verification(real_private_key, real_public_key):
    """Base32 encodes 5 data bits per character; a fixed-length blob whose
    bit-length isn't a multiple of 5 has a handful of trailing 'padding'
    bits in its last character that carry no real data (base32 masks them
    off on decode). Flipping one of those specific bits is a no-op, not a
    security gap - it never encoded anything the signature covers. This
    test pins that expectation down explicitly, so it can't later be
    mistaken for a regression: at least 95% of single-character edits
    across the whole key must be rejected."""
    key = codec.issue_license("RAM", real_private_key)
    total = 0
    rejected = 0
    for i, ch in enumerate(key):
        if ch == "-":
            continue
        total += 1
        tampered = key[:i] + ("A" if ch != "A" else "B") + key[i + 1:]
        try:
            codec.verify_license(tampered, public_key=real_public_key)
        except (InvalidLicenseFormatError, InvalidLicenseSignatureError):
            rejected += 1
    assert rejected / total >= 0.95


def test_long_student_name_is_truncated_not_rejected(real_private_key, real_public_key):
    long_name = "A" * 100
    key = codec.issue_license(long_name, real_private_key)
    payload = codec.verify_license(key, public_key=real_public_key)
    assert payload.student_tag == "A" * 32  # _STUDENT_TAG_MAX_BYTES


def test_blank_student_name_falls_back_to_placeholder(real_private_key, real_public_key):
    key = codec.issue_license("   ", real_private_key)
    payload = codec.verify_license(key, public_key=real_public_key)
    assert payload.student_tag == "STUDENT"
