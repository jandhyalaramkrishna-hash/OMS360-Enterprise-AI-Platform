"""
licensing/gate.py - the single entry point the launcher calls. Combines
codec.verify_license() + ActivationStore into the three operations the
launcher actually needs, so launcher/main.py doesn't have to know about
signature verification or MAC internals at all.
"""

from licensing.activation_store import ActivationStatus, ActivationStore
from licensing.codec import verify_license
from licensing.errors import LicenseError


class LicenseGate:
    def __init__(self, store: ActivationStore = None):
        self.store = store or ActivationStore()

    def current_status(self) -> ActivationStatus:
        """Call this first on every launch. If `.activated` is False, the
        app has never been activated on this machine - prompt for a key.
        If `.activated` is True and `.expired` is False, proceed straight
        to starting the application. If `.expired` is True, show the
        expiry message and exit (do NOT prompt for a new key - a new key
        does not extend an already-activated installation; see README.md)."""
        return self.store.read_status()

    def activate_with_key(self, key_str: str) -> ActivationStatus:
        """Call when the user submits a key in the first-run dialog.
        Raises a licensing.errors.LicenseError subclass on any invalid
        key (bad format / bad signature / unsupported version) - the
        caller (the UI dialog) should catch that and show its message,
        then let the user try again. Returns the resulting status on
        success (always `.activated=True`, `.expired=False` for a
        brand-new activation)."""
        payload = verify_license(key_str)  # raises LicenseError subclasses
        return self.store.record_activation(
            student_tag=payload.student_tag,
            license_id_hex=payload.license_id_hex,
            raw_key=payload.raw_key,
        )


__all__ = ["LicenseGate", "ActivationStatus", "LicenseError"]
