"""Tests for V2a shared-key license validation (core/license.py).

Hosted enforcement validates the per-request key against ``SPORTIQ_VALID_KEYS``;
when that is unset (local stdio) it falls back to the V1 presence check. The
``no_live_credentials`` autouse fixture blanks ``sportiq_valid_keys``, so the
default state here is "unset → presence mode"; the enforced tests set it.
"""
from __future__ import annotations

from sportiq import config as config_module
from sportiq.core.license import enforcement_active, validate_key

# -- unset (local) → presence fallback -----------------------------------------


def test_presence_fallback_when_unset():
    """No valid-key set configured → any non-blank key passes (V1 behaviour)."""
    assert enforcement_active() is False
    assert validate_key("sq_anything") is True
    assert validate_key("   ") is False
    assert validate_key("") is False


# -- configured (hosted) → membership ------------------------------------------


def test_membership_when_configured(monkeypatch):
    """Valid-key set configured → only members pass; everything else is rejected."""
    monkeypatch.setattr(config_module.settings, "sportiq_valid_keys", "sq_aaa, sq_bbb")
    assert enforcement_active() is True
    assert validate_key("sq_aaa") is True
    assert validate_key("sq_bbb") is True
    assert validate_key("sq_unknown") is False


def test_configured_set_rejects_blank(monkeypatch):
    """A blank key is never a member, even when enforcement is active."""
    monkeypatch.setattr(config_module.settings, "sportiq_valid_keys", "sq_aaa")
    assert validate_key("") is False
    assert validate_key("   ") is False


def test_single_key_set_parses(monkeypatch):
    """A one-key set (the launch Tier-0 shared key) is handled like any other."""
    monkeypatch.setattr(config_module.settings, "sportiq_valid_keys", "sq_solo")
    assert enforcement_active() is True
    assert validate_key("sq_solo") is True
    assert validate_key("sq_other") is False
