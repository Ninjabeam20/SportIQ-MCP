"""Tests for the V1 pro-entitlement gate (SPORTIQ_PRO_KEY presence check).

V1 is honor-system: any non-blank ``SPORTIQ_PRO_KEY`` unlocks the 24 intel tools;
absent/blank locks them with a ``SUBSCRIPTION_REQUIRED`` envelope. Free data tools
never check. The ``no_live_credentials`` autouse fixture blanks the key, so the
default state here is "locked"; unlocked tests set the one var.
"""
from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP

from sportiq import config as config_module
from sportiq.core.entitlements import (
    PAID_TOOLS,
    gated,
    get_active_key,
    is_pro,
    require_pro,
    reset_request_key,
    set_request_key,
)
from sportiq.core.errors import SubscriptionRequiredError
from sportiq.football.intel_tools import football_xg_model
from sportiq.football.tools import football_get_groups


async def _ok_tool() -> dict:
    """Stand-in async tool that always succeeds (gate pass-through probe)."""
    return {"data": {"ran": True}, "meta": {}}


# -- locked path (no key) ------------------------------------------------------


async def test_gate_locks_when_no_key():
    """No key → gated tool returns SUBSCRIPTION_REQUIRED, body never runs."""
    result = await gated(_ok_tool)()
    assert result["error"]["code"] == "SUBSCRIPTION_REQUIRED"


async def test_gate_locks_real_intel_tool_without_touching_chain():
    """A representative intel tool is gated; the chain is never reached when locked."""
    result = await gated(football_xg_model)(home_team="ARG", away_team="BRA")
    assert result["error"]["code"] == "SUBSCRIPTION_REQUIRED"
    assert result["error"]["suggestion"]  # carries the upgrade hint


# -- unlocked path -------------------------------------------------------------


async def test_gate_passes_through_when_key_present(monkeypatch):
    """Non-blank key → gated tool runs and returns its real envelope unchanged."""
    monkeypatch.setattr(config_module.settings, "sportiq_pro_key", "sq_test")
    result = await gated(_ok_tool)()
    assert result == {"data": {"ran": True}, "meta": {}}


async def test_blank_key_is_treated_as_locked(monkeypatch):
    """A present-but-blank key is not a valid key (honor-system stays off)."""
    monkeypatch.setattr(config_module.settings, "sportiq_pro_key", "   ")
    assert is_pro() is False
    assert get_active_key() is None


# -- V2a hosted enforcement (SPORTIQ_VALID_KEYS configured) --------------------


async def test_request_key_unlocks_when_valid_and_enforced(monkeypatch):
    """Host enforcing a valid-key set: a per-request key in the set unlocks."""
    monkeypatch.setattr(config_module.settings, "sportiq_valid_keys", "sq_good")
    token = set_request_key("sq_good")
    try:
        assert is_pro() is True
        require_pro()  # does not raise
        assert get_active_key() == "sq_good"
    finally:
        reset_request_key(token)


async def test_request_key_locks_when_invalid_and_enforced(monkeypatch):
    """Host enforcing a valid-key set: an unknown per-request key is rejected."""
    monkeypatch.setattr(config_module.settings, "sportiq_valid_keys", "sq_good")
    token = set_request_key("sq_bad")
    try:
        assert is_pro() is False
        result = await gated(_ok_tool)()
        assert result["error"]["code"] == "SUBSCRIPTION_REQUIRED"
    finally:
        reset_request_key(token)


async def test_invalid_key_message_differs_from_missing_key(monkeypatch):
    """An unrecognised key gets a distinct message from a missing key."""
    monkeypatch.setattr(config_module.settings, "sportiq_valid_keys", "sq_good")
    token = set_request_key("sq_bad")
    try:
        with pytest.raises(SubscriptionRequiredError) as exc:
            require_pro()
        assert "not recognised" in str(exc.value)
    finally:
        reset_request_key(token)


# -- free stays free -----------------------------------------------------------


async def test_free_tool_works_without_key():
    """A raw data tool is never gated — works with no key (static seed offline)."""
    result = await football_get_groups()
    assert result.get("error", {}).get("code") != "SUBSCRIPTION_REQUIRED"
    assert "data" in result


# -- paid-list coverage --------------------------------------------------------


async def test_every_paid_tool_registered_and_only_paid_tools_gated():
    """Mirror server.py registration: every PAID_TOOLS name is registered + gated,
    and no free tool is gated (the gated set equals PAID_TOOLS exactly)."""
    from sportiq.cricket.tools import register_cricket_tools
    from sportiq.f1.tools import register_f1_tools
    from sportiq.football.tools import register_football_tools
    from sportiq.server_tools.cross_sport import register_cross_sport_tools

    mcp = FastMCP("test")
    register_football_tools(mcp)
    register_f1_tools(mcp)
    register_cricket_tools(mcp)
    register_cross_sport_tools(mcp)

    tools = mcp._tool_manager._tools
    for name in PAID_TOOLS:
        assert name in tools, f"{name} not registered"
        assert getattr(tools[name].fn, "__sportiq_gated__", False), f"{name} not gated"

    gated_names = {n for n, t in tools.items() if getattr(t.fn, "__sportiq_gated__", False)}
    assert gated_names == set(PAID_TOOLS)
