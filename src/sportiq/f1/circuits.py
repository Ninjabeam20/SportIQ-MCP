"""Per-circuit profile loader — measured pit-loss / stop priors from F1DB.

Reads the committed ``data/circuits.json`` (built offline by
``scripts/build_f1_circuit_profiles.py`` from F1DB, CC BY 4.0). Keyed by OpenF1
``circuit_key`` so a live session resolves to a profile by exact integer lookup.
Pure, cached, no network. Unknown circuit -> ``None`` (tools fall back to the
generic 22.0s pit-loss default).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).parent / "data" / "circuits.json"


@lru_cache(maxsize=1)
def load_circuit_profiles() -> dict:
    if not _DATA.exists():
        return {}
    return json.loads(_DATA.read_text())


def profile_for_circuit_key(circuit_key: int | str | None) -> dict | None:
    """Return the circuit profile for an OpenF1 ``circuit_key``, or None."""
    if circuit_key is None:
        return None
    return load_circuit_profiles().get(str(circuit_key))
