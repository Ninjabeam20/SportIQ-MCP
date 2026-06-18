"""V1 pro-entitlement gate — honor-system presence check on ``SPORTIQ_PRO_KEY``.

Any non-blank key unlocks the 24 intelligence tools; absent/blank locks them with
a ``SUBSCRIPTION_REQUIRED`` envelope carrying the checkout link. Free data tools
never check. Zero network, zero new deps, provider-agnostic (a key from
Polar/LS/Paddle/Gumroad all work identically).

The ``get_active_key`` indirection and the ``gated`` wrapper are deliberate: V2
swaps ``get_active_key`` for a per-request contextvar + real Polar validation
*without touching any tool*. See docs/wiki/decisions/pro-entitlement-gate.md.
"""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import Any

from sportiq.config import settings
from sportiq.core.errors import SubscriptionRequiredError
from sportiq.core.tool_response import error_envelope

# Placeholder until the real Polar checkout link exists — swap this one string.
# V1 functions fully without it.
_UPGRADE = "https://polar.sh/sportiq/"

# The 24 paid tools — everything in the 4 intel/cross-sport modules. The ~19 raw
# data tools in */tools.py and sportiq_health stay free. Locked 2026-06-18.
PAID_TOOLS: frozenset[str] = frozenset(
    {
        # football/intel_tools.py (8)
        "football_xg_model",
        "football_match_predictor",
        "football_simulate_group",
        "football_simulate_bracket",
        "football_knockout_path",
        "football_find_value_bets",
        "football_form_trends",
        "football_build_accumulator",
        # f1/intel_tools.py (7)
        "f1_tyre_degradation",
        "f1_undercut_window",
        "f1_head_to_head_pace",
        "f1_weather_strategy_impact",
        "f1_predict_pit_strategy",
        "f1_qualifying_analysis",
        "f1_race_pace_compare",
        # cricket/intel_tools.py (8)
        "cricket_build_dream11_team",
        "cricket_captain_recommendation",
        "cricket_differential_picks",
        "cricket_player_form_index",
        "cricket_get_pitch_report",
        "cricket_head_to_head",
        "cricket_find_value_bets",
        "cricket_player_matchup",
        # server_tools/cross_sport.py (1)
        "cross_sport_build_accumulator",
    }
)


def get_active_key() -> str | None:
    """Return the active pro key, or None when absent/blank.

    V1: reads the single process-wide ``settings.sportiq_pro_key``. V2 replaces
    this body with a per-request contextvar lookup — tools call ``is_pro`` /
    ``require_pro``, never this directly, so they stay unchanged.
    """
    key = settings.sportiq_pro_key
    return key if key and key.strip() else None


def is_pro() -> bool:
    """True when a non-blank pro key is active."""
    return get_active_key() is not None


def require_pro() -> None:
    """Raise ``SubscriptionRequiredError`` when no pro key is active."""
    if not is_pro():
        raise SubscriptionRequiredError(
            "This is a SportIQ Pro tool. Set SPORTIQ_PRO_KEY in your MCP client "
            "config to unlock the intelligence tools."
        )


def gated(
    fn: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    """Wrap a tool coroutine so it requires an active pro key.

    On entry calls ``require_pro``; on lock returns a ``SUBSCRIPTION_REQUIRED``
    envelope (the tool body never runs). ``functools.wraps`` preserves the name,
    docstring, and signature so the FastMCP schema is unchanged. The
    ``__sportiq_gated__`` marker lets registration tests assert exactly the paid
    set is wrapped.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            require_pro()
        except SubscriptionRequiredError as e:
            return error_envelope(
                code="SUBSCRIPTION_REQUIRED",
                message=e.message,
                suggestion=f"Subscribe at {_UPGRADE} then set SPORTIQ_PRO_KEY.",
            )
        return await fn(*args, **kwargs)

    wrapper.__sportiq_gated__ = True  # type: ignore[attr-defined]
    return wrapper
