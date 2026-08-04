"""
licensing/ - OMS360 Enterprise AI Platform Student Practice Kit licensing layer.

Deliberately kept 100% separate from the OMS360 business logic (app/, ai/).
Nothing in this package imports from, or is imported by, app/ or ai/ - the
launcher composes them at the process level only (it starts the real,
unmodified `app.main:app` FastAPI application after this package clears the
license gate; it never edits or patches it).

Design summary (see README.md in this folder for the full write-up):

- Asymmetric (Ed25519) signing, per explicit requirement. The main
  application (OMS360 Enterprise AI Platform.exe) ships with ONLY the
  public key (`licensing.keys.PUBLIC_KEY_HEX`) - it can verify a license,
  it cannot mint one. Only OMS360 License Generator.exe carries the
  private key, and even there it is never displayed in the UI.
- A license "key" is a self-contained, offline-verifiable, signed token
  (student tag + a random license id + issue time, Ed25519-signed).
  There is no server and no phone-home - verification is entirely local
  against the embedded public key.
- The 7-day clock starts at *first successful activation on the student's
  machine*, not at generation time - `activation_store.py` records that
  moment locally (with a tamper-evident local MAC) and every subsequent
  launch just checks "now < activated_at + 7 days".
- Honest limitation, stated plainly rather than oversold: this is a
  reasonable, proportionate evaluation gate for a short student practice
  kit, not hardened DRM. A technically sophisticated student who locates
  and clears both the local activation record and its guard secret could
  reset the local trial window on the same key. There is no backend to
  prevent that for a fully offline tool - the same limitation every
  offline shareware/trialware product has. See README.md, section
  "Security model and its limits".
"""
