"""The committed venues.json (Cricsheet-regenerated 1st/2nd-innings averages) must
keep its exact schema and stay in sane T20 ranges, so the pitch_report / captain
models that read it never see a malformed or out-of-band record."""
from __future__ import annotations

import json
from pathlib import Path

_VENUES = Path(__file__).resolve().parents[2] / "src" / "sportiq" / "cricket" / "data" / "venues.json"
_FIELDS = {"name", "city", "pitch_type", "avg_first_innings", "avg_chasing", "boundary_size_m"}


def _load() -> dict:
    return json.loads(_VENUES.read_text())


def test_venues_schema_is_uniform_and_in_band():
    venues = _load()
    assert len(venues) >= 13
    for key, rec in venues.items():
        assert set(rec) == _FIELDS, f"{key} has unexpected fields {set(rec)}"
        assert rec["pitch_type"] in {"batting", "bowling", "balanced"}
        # Modern IPL first-innings totals sit well inside this band.
        assert 140 <= rec["avg_first_innings"] <= 230
        # Chasing average is the 2nd-innings total — at or below first innings.
        assert rec["avg_chasing"] <= rec["avg_first_innings"]
        assert rec["boundary_size_m"] > 0


def test_regen_lifted_high_scoring_venues():
    """Sanity that the Cricsheet regen actually applied: Eden Gardens, a measured
    high-scoring ground, now reads well above the old hand-set 168."""
    assert _load()["eden_gardens"]["avg_first_innings"] >= 180
