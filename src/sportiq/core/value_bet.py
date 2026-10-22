"""Core value-bet math — shared by cricket and football tools.

Pure functions, no I/O. These are the canonical implementations; the
sport-specific modules re-export from here so existing imports continue to work.

A bookmaker's decimal prices imply probabilities that sum to **more** than 1 —
the excess is the bookmaker's margin ("vig" / "overround"). De-vigging normalises
the implied probabilities back to sum 1 so they're comparable to a true probability.
An outcome is flagged as value only when ``model_prob`` exceeds the de-vigged
market probability by ``min_edge`` **and** the offered price has positive expected
value (``model_prob * market_odds - 1 > 0``). Edge alone is not enough: a 51%
model vs 1.90/3.00/3.00 shows a +6.88 pp edge but returns -3.10% at 1.90.
"""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite

# Map a market outcome key to the model's probability key.
_OUTCOME_TO_MODEL = {"home": "home_win", "draw": "draw", "away": "away_win"}


def implied_prob(decimal_odds: float) -> float:
    """Implied probability of a decimal price: ``1 / odds``."""
    if decimal_odds <= 0:
        raise ValueError("decimal_odds must be positive")
    return 1.0 / decimal_odds


def devig(probs: dict[str, float]) -> dict[str, float]:
    """Normalise per-outcome implied probabilities to sum to 1 (multiplicative method).

    The multiplicative (a.k.a. proportional) method divides each implied
    probability by the overround (their sum). It's the simplest de-vig and assumes
    the margin is applied proportionally across outcomes — adequate for 1X2 markets
    where we only need a comparison baseline, not a calibrated true price.

    Empty / all-zero input returns ``{}``.
    """
    total = sum(probs.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in probs.items()}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def has_commenced(event: dict, now: datetime | None = None) -> bool:
    """True when the event's ``commence_time`` (ISO 8601, UTC) is at or before now.

    Started or in-play events are not priced against a pre-match model. A missing
    or unparseable time is treated as not started.
    """
    raw = event.get("commence_time")
    if not raw:
        return False
    try:
        start = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    return start <= (now or _utcnow())


def find_value(
    model_probs: dict[str, float],
    bookmaker: dict,
    min_edge: float,
) -> list[dict]:
    """Return +EV picks for one bookmaker's 1X2 prices.

    Args:
        model_probs: ``{home_win, draw, away_win}`` from the match model.
        bookmaker: ``{name, home, draw, away}`` decimal prices (any may be None).
        min_edge: minimum ``model_prob - devigged_market_prob`` to flag as value.
            The price must also have positive expected value.

    Returns:
        One dict per value outcome:
        ``{outcome, model_prob, fair_odds, market_odds, edge, ev_pct, bookmaker,
        price_updated_at}``. ``ev_pct`` is ``(model_prob * market_odds - 1) * 100``;
        ``price_updated_at`` is the bookmaker's ``last_update`` (None if absent).
        Outcomes with a missing (None), non-positive, non-finite, or non-numeric price are skipped.
    """
    # Implied probs only for outcomes that carry a price.
    implied: dict[str, float] = {}
    prices: dict[str, float] = {}
    for outcome in _OUTCOME_TO_MODEL:
        raw = bookmaker.get(outcome)
        if raw is None:
            continue
        try:
            price = float(raw)
        except (TypeError, ValueError):
            continue
        if not isfinite(price) or price <= 0:
            continue
        implied[outcome] = implied_prob(price)
        prices[outcome] = price
    devigged = devig(implied)

    picks: list[dict] = []
    for outcome, market_prob in devigged.items():
        model_prob = model_probs.get(_OUTCOME_TO_MODEL[outcome])
        if model_prob is None:
            continue
        edge = model_prob - market_prob
        ev = model_prob * prices[outcome] - 1
        if edge >= min_edge and ev > 0:
            picks.append(
                {
                    "outcome": outcome,
                    "model_prob": round(model_prob, 4),
                    "fair_odds": round(1.0 / model_prob, 3) if model_prob > 0 else None,
                    "market_odds": bookmaker[outcome],
                    "edge": round(edge, 4),
                    "ev_pct": round(ev * 100, 2),
                    "bookmaker": bookmaker.get("name"),
                    "price_updated_at": bookmaker.get("last_update"),
                }
            )
    return picks
