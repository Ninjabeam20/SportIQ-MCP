"""Pro-entitlement gate for the 24 intelligence tools.

Resolves the active key (per-request contextvar on the hosted ``/mcp``, else the
``SPORTIQ_PRO_KEY`` env var) and validates it via ``core/license.validate_key``:
membership in ``SPORTIQ_VALID_KEYS`` when configured (hosted enforcement, V2a),
otherwise a non-blank presence check (local stdio, V1). A locked call returns a
``SUBSCRIPTION_REQUIRED`` envelope carrying the upgrade link; free data tools
never check. Provider-agnostic — any issued key works through the same path.

The ``get_active_key`` indirection and the ``gated`` wrapper are deliberate: the
key source and validator can change *without touching any tool*. See
docs/wiki/decisions/0011-pro-entitlement-gate.md.
"""

from __future__ import annotations

import contextvars
import functools
from collections.abc import Awaitable, Callable
from typing import Any

from sportiq.config import settings
from sportiq.core.errors import SubscriptionRequiredError
from sportiq.core.license import validate_key
from sportiq.core.tool_response import error_envelope

# GitHub Sponsors is the primary monetization path. This is the upgrade link
# shown in the lock message; the gate is provider-agnostic (any non-blank key
# unlocks), so swapping this one string is all a provider change needs.
_UPGRADE = "https://github.com/sponsors/Ninjabeam20"

# Public hosted base. Sponsors unlock the hosted intel tools by adding their
# personal connector link `<_HOSTED>/u/<key>/mcp` (claude.ai / ChatGPT have no
# key field — the key rides in the URL). Local installs set SPORTIQ_PRO_KEY.
_HOSTED = "https://sportiq-mcp-329580761892.us-central1.run.app"

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


# Per-request Pro key for the hosted /mcp (multi-tenant). ``ProKeyMiddleware``
# sets this from the request (URL path or header) so each call validates *that
# user's* key; reset after the request. Unset on stdio (single-user local).
_request_key: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "sportiq_request_key", default=None
)


def set_request_key(key: str | None) -> contextvars.Token:
    """Bind the Pro key for the current request (hosted /mcp middleware).

    Returns a token the caller MUST pass to ``reset_request_key`` when the
    request ends, so a key never leaks across requests on a reused worker task.
    """
    return _request_key.set(key)


def reset_request_key(token: contextvars.Token) -> None:
    """Clear the per-request Pro key bound by ``set_request_key``."""
    _request_key.reset(token)


def get_active_key() -> str | None:
    """Return the active pro key, or None when absent/blank.

    Resolution order: (1) the per-request contextvar set by ``ProKeyMiddleware``
    on the hosted ``/mcp`` (multi-tenant), then (2) the process-wide
    ``settings.sportiq_pro_key`` env var (single-user local stdio). Tools call
    ``is_pro`` / ``require_pro``, never this directly, so they stay unchanged.
    """
    rk = _request_key.get()
    if rk and rk.strip():
        return rk
    key = settings.sportiq_pro_key
    return key if key and key.strip() else None


def is_pro() -> bool:
    """True when a present pro key is also a *valid* key.

    On the host (``SPORTIQ_VALID_KEYS`` set) this means membership in the valid
    set; locally it means any non-blank key (V1 presence check). See
    ``core/license.validate_key``.
    """
    key = get_active_key()
    return key is not None and validate_key(key)


def require_pro() -> None:
    """Raise ``SubscriptionRequiredError`` when no *valid* pro key is active."""
    key = get_active_key()
    if key is None:
        raise SubscriptionRequiredError(
            "This is a SportIQ Pro tool. Set SPORTIQ_PRO_KEY in your MCP client "
            "config to unlock the intelligence tools."
        )
    if not validate_key(key):
        raise SubscriptionRequiredError(
            "This SportIQ Pro key was not recognised. Check the key from your "
            "sponsorship welcome message, or subscribe to get one."
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
                suggestion=(
                    f"Sponsor at {_UPGRADE} to get a Pro key. Local install: set "
                    f"SPORTIQ_PRO_KEY. In claude.ai or ChatGPT: add your personal "
                    f"connector link {_HOSTED}/u/<your-key>/mcp (from your welcome "
                    f"email) as a custom connector with No authentication."
                ),
            )
        return await fn(*args, **kwargs)

    wrapper.__sportiq_gated__ = True  # type: ignore[attr-defined]
    return wrapper
