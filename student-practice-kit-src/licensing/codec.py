"""
licensing/codec.py - License payload <-> pretty key string, signing and
verification.

Payload layout (before signing), all big-endian:
    byte 0        version            (licensing.keys.LICENSE_FORMAT_VERSION)
    byte 1        student_tag_len    (0-32)
    bytes 2..N    student_tag        (UTF-8, N = student_tag_len bytes)
    next 4 bytes  license_id         (random, uniqueness/serial - NOT a secret)
    next 4 bytes  issued_at_unix     (uint32 seconds since epoch, UTC)

Signed blob = payload + Ed25519_signature(payload)   (signature is 64 bytes)

Pretty key = "ZELQA-OMS360-" + base32(signed blob), grouped in 5-char
blocks separated by dashes. Base32 (not base64) is deliberate: it's
case-insensitive and skips visually-confusable characters (0/O, 1/I/l),
which matters because a student may be reading this off a screen and
typing it, or an instructor may be reading it aloud.

Why the key is longer than a typical product key: a genuinely
unforgeable, fully-offline-verifiable *asymmetric* signature (Ed25519)
is 64 bytes on its own - about 103 base32 characters before you even add
the payload. Short "XXXX-XXXX-XXXX" style keys are only achievable with a
symmetric checksum, which is a materially weaker guarantee (the secret
that checks it has to live inside every copy of the app, whereas Ed25519
verification only ever needs the public key). Sprint's explicit "standard
cryptographic signing (public/private key)" requirement is honored
literally here rather than substituted for a shorter but weaker scheme.
The result is fully copy/paste-able (both apps accept pasted text with or
without surrounding whitespace/newlines), just not something you'd
type from memory - which matches how real asymmetric license files work
in practice.
"""

import base64
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from licensing import keys
from licensing.errors import (
    InvalidLicenseFormatError,
    InvalidLicenseSignatureError,
    UnsupportedLicenseVersionError,
)

_SIGNATURE_LEN = 64
_STUDENT_TAG_MAX_BYTES = 32


class LicensePayload:
    """Parsed, verified contents of a license key. Immutable by convention
    (nothing in this codebase mutates an instance after construction)."""

    __slots__ = ("version", "student_tag", "license_id", "issued_at_unix", "raw_key")

    def __init__(self, version, student_tag, license_id, issued_at_unix, raw_key):
        self.version = version
        self.student_tag = student_tag
        self.license_id = license_id          # bytes, 4 bytes, hex-displayable
        self.issued_at_unix = issued_at_unix
        self.raw_key = raw_key                # the exact pretty-key string this came from

    @property
    def license_id_hex(self) -> str:
        return self.license_id.hex()

    def __repr__(self):
        return (
            f"LicensePayload(student_tag={self.student_tag!r}, "
            f"license_id={self.license_id_hex}, issued_at_unix={self.issued_at_unix})"
        )


def _encode_payload(student_tag: str, license_id: bytes, issued_at_unix: int) -> bytes:
    tag_bytes = student_tag.encode("utf-8")[:_STUDENT_TAG_MAX_BYTES]
    if len(license_id) != 4:
        raise ValueError("license_id must be exactly 4 bytes")
    out = bytearray()
    out.append(keys.LICENSE_FORMAT_VERSION)
    out.append(len(tag_bytes))
    out.extend(tag_bytes)
    out.extend(license_id)
    out.extend(int(issued_at_unix).to_bytes(4, "big"))
    return bytes(out)


def _decode_payload(payload: bytes):
    if len(payload) < 2:
        raise InvalidLicenseFormatError("License payload too short.")
    version = payload[0]
    if version != keys.LICENSE_FORMAT_VERSION:
        raise UnsupportedLicenseVersionError(
            f"License was issued with format version {version}, "
            f"this build understands version {keys.LICENSE_FORMAT_VERSION}."
        )
    tag_len = payload[1]
    offset = 2
    if len(payload) < offset + tag_len + 4 + 4:
        raise InvalidLicenseFormatError("License payload is truncated.")
    student_tag = payload[offset:offset + tag_len].decode("utf-8", errors="replace")
    offset += tag_len
    license_id = payload[offset:offset + 4]
    offset += 4
    issued_at_unix = int.from_bytes(payload[offset:offset + 4], "big")
    return version, student_tag, license_id, issued_at_unix


def _pretty_encode(blob: bytes) -> str:
    b32 = base64.b32encode(blob).decode("ascii")   # includes '=' padding
    core = b32.rstrip("=")
    grouped = "-".join(core[i:i + 5] for i in range(0, len(core), 5))
    return f"{keys.KEY_PREFIX}{grouped}"


def _pretty_decode(key_str: str) -> bytes:
    s = "".join(key_str.split())  # strip all whitespace/newlines (paste-friendly)
    s = s.upper()
    if not s.startswith(keys.KEY_PREFIX):
        raise InvalidLicenseFormatError(
            f"License key must start with '{keys.KEY_PREFIX}'."
        )
    core = s[len(keys.KEY_PREFIX):].replace("-", "")
    if not core:
        raise InvalidLicenseFormatError("License key has no data after the prefix.")
    pad_len = (-len(core)) % 8
    b32 = core + ("=" * pad_len)
    try:
        return base64.b32decode(b32)
    except Exception as exc:
        raise InvalidLicenseFormatError(f"License key is not valid base32: {exc}") from exc


def issue_license(student_name: str, private_key: Ed25519PrivateKey) -> str:
    """Generator-side only. Mints a new, uniquely-signed license key for
    `student_name`. Never called from the launcher/main app - that side
    only ever verifies."""
    import os

    student_tag = student_name.strip() or "STUDENT"
    license_id = os.urandom(4)
    issued_at_unix = int(time.time())

    payload = _encode_payload(student_tag, license_id, issued_at_unix)
    signature = private_key.sign(payload)
    blob = payload + signature
    return _pretty_encode(blob)


def verify_license(key_str: str, public_key: Ed25519PublicKey = None) -> LicensePayload:
    """Launcher-side. Raises InvalidLicenseFormatError /
    UnsupportedLicenseVersionError / InvalidLicenseSignatureError on any
    problem; returns a LicensePayload only if the signature genuinely
    verifies against the embedded public key."""
    if public_key is None:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(keys.PUBLIC_KEY_HEX))

    blob = _pretty_decode(key_str)
    if len(blob) <= _SIGNATURE_LEN:
        raise InvalidLicenseFormatError("License key is too short to contain a signature.")

    payload = blob[:-_SIGNATURE_LEN]
    signature = blob[-_SIGNATURE_LEN:]

    try:
        public_key.verify(signature, payload)
    except InvalidSignature as exc:
        raise InvalidLicenseSignatureError(
            "This key was not issued by OMS360 License Generator.exe "
            "(signature does not verify), or it has been altered."
        ) from exc

    version, student_tag, license_id, issued_at_unix = _decode_payload(payload)
    return LicensePayload(
        version=version,
        student_tag=student_tag,
        license_id=license_id,
        issued_at_unix=issued_at_unix,
        raw_key="".join(key_str.split()).upper(),
    )
