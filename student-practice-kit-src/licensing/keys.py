"""
licensing/keys.py - Embedded Ed25519 key material.

PUBLIC KEY: safe to embed anywhere. Ships inside BOTH compiled executables.
Verifying a signature with it proves the license was minted by someone who
holds the matching private key - it cannot be used to mint new licenses.

PRIVATE KEY: must only ever be used inside OMS360 License Generator.exe,
and never rendered in that app's UI (the UI only ever shows the *resulting*
license key text, never this constant). It is kept in its own module,
lightly split/obfuscated rather than a single obvious "PRIVATE_KEY = ..."
string, so it is not the very first thing a casual `strings` scan of the
built binary turns up.

Honest limitation: this is Python, distributed via PyInstaller. PyInstaller
does not encrypt or obfuscate bytecode by default, and even with its
optional AES cipher, a determined reverse engineer can eventually recover
embedded constants from any offline binary - no client-side secret is ever
truly unextractable. Splitting/XOR-ing the private key bytes here raises
the bar above a trivial `strings` grep; it is not a claim of unbreakable
protection. If ZelQA Technologies ever needs stronger guarantees, the
options are: keep the Generator on a machine nobody but staff touches
(the actual mitigation that matters), and/or move signing behind a small
internal server instead of an embedded constant. Both are explicitly out
of scope for this practice kit.

Regenerating these keys: run `python build/generate_keypair.py` once, then
paste its output into this file (PUBLIC_KEY_HEX) and into
`generator/_signing_key.py` (the split private key). Do this only if the
existing key pair is ever suspected compromised - regenerating invalidates
every license key issued under the old pair, since the main app only
trusts the public key embedded in the copy it was built from.
"""

# Ed25519 public key, raw 32 bytes, hex-encoded. Generated once via
# build/generate_keypair.py and frozen here. Embedded in BOTH executables.
PUBLIC_KEY_HEX = "a5a2073c9a437071b9d64ab08364a18d7e00f80093ccc4050843f3b5bdf6e2cc"

# Format version for the license payload encoding (licensing/codec.py).
# Bump this if the payload layout ever changes, so old/new keys/binaries
# fail cleanly instead of silently misparsing each other.
LICENSE_FORMAT_VERSION = 1

# The one and only supported evaluation duration. Not read from anywhere
# configurable (no env var, no CLI flag, no UI field) - this is the single
# source of truth both apps import, so "no other duration is ever allowed"
# is structural, not a policy someone could accidentally override.
LICENSE_DURATION_DAYS = 7

BRAND_NAME = "OMS360 Enterprise AI Platform"
BRAND_COMPANY = "ZelQA Technologies"
KEY_PREFIX = "ZELQA-OMS360-"

# --- Cosmetic app metadata ---------------------------------------------------
# The four constants below are display-only strings used by every Tkinter
# window in launcher/ and generator/ (splash, activation/login dialog,
# status window, About dialog, Version dialog) so branding text lives in
# exactly one place rather than being retyped per-window. None of these
# affect licensing behavior - LICENSE_DURATION_DAYS above is the only
# constant here that does.
BRAND_VERSION = "1.0.0"
BRAND_EDITION = "Student Practice Edition"
BRAND_TAGLINE = f"{BRAND_NAME} — {BRAND_EDITION}"
BRAND_COPYRIGHT = f"© {BRAND_COMPANY}. All Rights Reserved."
