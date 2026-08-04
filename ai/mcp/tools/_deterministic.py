"""
AI Service Layer - MCP - Mock Tools - deterministic selection helper
OMS-360 Enterprise Food Delivery Platform

Every mock tool in this package needs to turn an arbitrary caller-supplied
id string into one of a small set of canned mock values, the same way on
every call for the same id (so tests and callers get stable, reproducible
mock responses) while still varying across different ids (so the mock
data doesn't look obviously hardcoded). This is deliberately NOT Python's
`random` module - there is no randomness here, only a fixed function of
the input string, so results never differ between runs or processes.
"""


def pick(seed: str, options: tuple):
    """Deterministically selects one item from `options` based on `seed`.
    Same seed always yields the same item; different seeds are spread
    across the option set via a simple checksum of the seed's characters."""
    if not options:
        raise ValueError("options must be non-empty.")
    checksum = sum(ord(ch) for ch in seed) if seed else 0
    return options[checksum % len(options)]


def pick_int(seed: str, minimum: int, maximum: int) -> int:
    """Deterministically selects an integer in [minimum, maximum]
    (inclusive) based on `seed`, using the same checksum approach as
    pick()."""
    if maximum < minimum:
        raise ValueError("maximum must be >= minimum.")
    span = maximum - minimum + 1
    checksum = sum(ord(ch) for ch in seed) if seed else 0
    return minimum + (checksum % span)
