"""Value-bet detector — compare de-vigged bookmaker odds to a model's probabilities.

Pure functions, no I/O. The tool layer (``football_find_value_bets``) supplies the
model probabilities (from the same Poisson/Elo path ``football_match_predictor``
uses) and the per-bookmaker decimal odds; this module does the probability math.

Re-exports the canonical implementations from ``sportiq.core.value_bet`` so that
existing imports continue to work unchanged.
"""
from __future__ import annotations

# Re-export from core so existing imports continue to work.
from sportiq.core.value_bet import _OUTCOME_TO_MODEL, devig, find_value, implied_prob

__all__ = ["_OUTCOME_TO_MODEL", "devig", "find_value", "implied_prob"]
