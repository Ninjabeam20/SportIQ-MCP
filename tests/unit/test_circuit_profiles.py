"""The committed circuits.json (F1DB-derived) must be well-formed, and a
circuit's measured pit loss must actually move the undercut verdict."""
from __future__ import annotations

from sportiq.f1.circuits import load_circuit_profiles, profile_for_circuit_key
from sportiq.f1.models.undercut import undercut_window


def test_profiles_load_with_sane_shape():
    profiles = load_circuit_profiles()
    assert len(profiles) >= 20  # current calendar is ~24 circuits
    for key, p in profiles.items():
        assert key.isdigit()  # keyed by OpenF1 circuit_key
        assert 15.0 <= p["pit_loss_s"] <= 45.0
        assert p["typical_stops"] >= 1
        assert p["lap_length_km"] > 0
        assert isinstance(p["circuit"], str) and p["circuit"]
        assert p["sample_size"] > 0


def test_unknown_circuit_key_returns_none():
    assert profile_for_circuit_key(999999) is None
    assert profile_for_circuit_key(None) is None


def test_pit_loss_spread_changes_undercut_verdict():
    """Two real circuits with different measured pit loss give different undercut
    math for identical pace/gap inputs — the whole point of per-circuit profiles."""
    profiles = load_circuit_profiles()
    losses = sorted(p["pit_loss_s"] for p in profiles.values())
    low, high = losses[0], losses[-1]
    assert high - low >= 3.0  # meaningful spread vs the old flat 22.0s

    # Attacker clearly faster so the undercut resolves in a countable number of
    # laps; only pit_loss_s differs between the two calls.
    kw = dict(driver_pace_s=80.0, target_pace_s=83.0, fresh_tyre_delta_s=1.5, gap_to_target_s=2.0)
    verdict_low = undercut_window(pit_loss_s=low, **kw)
    verdict_high = undercut_window(pit_loss_s=high, **kw)
    assert verdict_low["laps_to_clear"] != verdict_high["laps_to_clear"]
