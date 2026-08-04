"""
generator/_signing_key.py - the Ed25519 PRIVATE key, used only by
OMS360 License Generator.exe to sign new license keys.

This module is imported by generator/main.py only - never by
launcher/main.py or anything under licensing/ that ships inside the
student-facing app. That app carries only licensing.keys.PUBLIC_KEY_HEX.

Why the value below isn't a single obvious `PRIVATE_KEY_HEX = "..."`
constant: see licensing/keys.py's module docstring for the full, honest
explanation of what this obfuscation does and does not achieve (raises
the bar above a trivial `strings` scan of the compiled .exe; does not
make the key un-extractable from an offline Python/PyInstaller binary -
nothing can). The two halves below are combined with XOR at import time
to reconstruct the real 32-byte Ed25519 seed.
"""

_PAD_HEX = "86dd92884f19e5e3c8df9a9f4cc2c5e9756c96d843e61589168fc9b5592bb850"
_XORED_HEX = "d7fd6988b56663de12836421e6e568ec24f953e6a1e15753caacbcff37117729"


def _reconstruct() -> bytes:
    pad = bytes.fromhex(_PAD_HEX)
    xored = bytes.fromhex(_XORED_HEX)
    return bytes(a ^ b for a, b in zip(xored, pad))


def load_private_key():
    """Returns an Ed25519PrivateKey. Imported lazily by generator/main.py
    right before signing, not held as a module-level object, so it isn't
    sitting resolved in memory/globals for longer than it needs to be."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    seed = _reconstruct()
    try:
        return Ed25519PrivateKey.from_private_bytes(seed)
    finally:
        # Best-effort scrub of the local reference; CPython bytes objects
        # are immutable so this does not guarantee the value is wiped
        # from memory - documented as best-effort, not a real guarantee.
        del seed
