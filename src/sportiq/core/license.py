"""V2a hosted license validation — shared-key enforcement.

On the hosted ``/mcp`` the per-request Pro key is validated against a configured
set of valid keys (``SPORTIQ_VALID_KEYS``, a Cloud Run secret). This is the first
online-enforcement phase: one shared set, no per-user identity yet. V2b swaps
``SharedKeyValidator`` for a keystore-backed validator (filled by the GitHub
``sponsorship`` webhook) behind the same ``LicenseValidator`` Protocol — the gate
(``require_pro`` in ``core/entitlements.py``) never changes.

When ``SPORTIQ_VALID_KEYS`` is unset (local stdio / uvx) there is nothing to
validate against, so the gate falls back to the V1 presence check: any non-blank
key unlocks. Local installs are open-source Python and uncrackable anyway —
enforcement only has teeth on the server we own. See
docs/wiki/decisions/0011-pro-entitlement-gate.md.
"""

from __future__ import annotations

import functools
from typing import Protocol, runtime_checkable

from sportiq.config import settings


@runtime_checkable
class LicenseValidator(Protocol):
    """A key-validation strategy. V2a = shared set; V2b = keystore lookup."""

    @property
    def configured(self) -> bool:
        """True when this validator has a key source to enforce against."""
        ...

    def validate(self, key: str) -> bool:
        """True when ``key`` is a recognised, active Pro key."""
        ...


@functools.lru_cache(maxsize=8)
def _parse(raw: str | None) -> frozenset[str]:
    """Parse the comma-separated ``SPORTIQ_VALID_KEYS`` into a set.

    Cached on the raw string so the hot path (every gated call) does no work
    after the first parse; a different raw value (tests, secret rotation +
    restart) is simply a distinct cache entry.
    """
    if not raw:
        return frozenset()
    return frozenset(k.strip() for k in raw.split(",") if k.strip())


class SharedKeyValidator:
    """V2a: validate against the configured ``SPORTIQ_VALID_KEYS`` set.

    Reads ``settings`` live each call (parse is cached) so a value set after
    construction — tests, or a restarted host with a rotated secret — is honoured.
    """

    @property
    def configured(self) -> bool:
        return bool(_parse(settings.sportiq_valid_keys))

    def validate(self, key: str) -> bool:
        return key in _parse(settings.sportiq_valid_keys)


# Module-level singleton; V2b swaps this for a KeystoreValidator.
_VALIDATOR: LicenseValidator = SharedKeyValidator()


def enforcement_active() -> bool:
    """True when a valid-key source is configured (hosted) — the gate enforces
    membership rather than the V1 presence check."""
    return _VALIDATOR.configured


def validate_key(key: str) -> bool:
    """Return True when ``key`` may unlock the paid tools.

    Hosted (``SPORTIQ_VALID_KEYS`` set): the key must be a member of the set.
    Local (unset): fall back to the V1 presence check — any non-blank key passes
    (local enforcement is best-effort; the server we own is the real gate).
    """
    if not _VALIDATOR.configured:
        return bool(key and key.strip())
    return _VALIDATOR.validate(key)
