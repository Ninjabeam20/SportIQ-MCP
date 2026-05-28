"""F1 tyre compound constants -- static seeds for the pit-strategy model.

Values are seeded from public 2024-25 race-engineer references.
Per-race auto-calibration is a Phase 3.1 follow-up.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TyreCompound(StrEnum):
    SOFT = "SOFT"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    INTER = "INTER"
    WET = "WET"


@dataclass(frozen=True)
class TyreSpec:
    compound: TyreCompound
    base_lap_delta_s: float      # seconds vs reference (MEDIUM=0); negative = faster
    degradation_rate_s_per_lap: float  # linear time loss per lap on this compound
    safe_window_laps: int        # typical stint length before cliff
    crossover_lap: int           # lap where next compound overtakes this one


TYRE_SPECS: dict[TyreCompound, TyreSpec] = {
    TyreCompound.SOFT: TyreSpec(
        compound=TyreCompound.SOFT,
        base_lap_delta_s=-0.8,
        degradation_rate_s_per_lap=0.08,
        safe_window_laps=15,
        crossover_lap=12,
    ),
    TyreCompound.MEDIUM: TyreSpec(
        compound=TyreCompound.MEDIUM,
        base_lap_delta_s=0.0,
        degradation_rate_s_per_lap=0.05,
        safe_window_laps=25,
        crossover_lap=20,
    ),
    TyreCompound.HARD: TyreSpec(
        compound=TyreCompound.HARD,
        base_lap_delta_s=0.6,
        degradation_rate_s_per_lap=0.03,
        safe_window_laps=40,
        crossover_lap=35,
    ),
    TyreCompound.INTER: TyreSpec(
        compound=TyreCompound.INTER,
        base_lap_delta_s=3.0,
        degradation_rate_s_per_lap=0.10,
        safe_window_laps=20,
        crossover_lap=15,
    ),
    TyreCompound.WET: TyreSpec(
        compound=TyreCompound.WET,
        base_lap_delta_s=6.0,
        degradation_rate_s_per_lap=0.12,
        safe_window_laps=15,
        crossover_lap=10,
    ),
}
