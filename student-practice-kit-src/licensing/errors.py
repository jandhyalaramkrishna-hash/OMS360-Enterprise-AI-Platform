"""licensing/errors.py - exceptions raised by the licensing package."""


class LicenseError(Exception):
    """Base class for every licensing-related error."""


class InvalidLicenseFormatError(LicenseError):
    """The provided text is not shaped like an OMS360 license key at all
    (wrong prefix, not valid base32, wrong decoded length)."""


class InvalidLicenseSignatureError(LicenseError):
    """The text decodes to a well-formed payload, but the signature does
    not verify against the embedded public key - it was not issued by
    OMS360 License Generator.exe (or the payload was altered)."""


class UnsupportedLicenseVersionError(LicenseError):
    """The payload's format-version byte is not one this build understands
    (e.g. a key minted by a newer/older Generator than this app supports)."""


class ActivationStateCorruptError(LicenseError):
    """A local activation record exists but failed its tamper-evidence
    check. Treated as expired (fail closed) - see activation_store.py."""


class EvaluationExpiredError(LicenseError):
    """The 7-day evaluation window (from first successful activation) has
    elapsed."""
