"""Tool-layer fixtures."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


@pytest.fixture(autouse=True)
def _pre_tournament_clock(monkeypatch: pytest.MonkeyPatch):
    """Freeze the value-bet clock before the recorded 2026 odds events.

    The find-value tools skip events whose ``commence_time`` has passed
    (``core.value_bet.has_commenced``). Recorded odds payloads carry real 2026
    kickoff times, so without this every one would read as already started.
    Tests that exercise the started-event filter patch ``_utcnow`` themselves.
    """
    monkeypatch.setattr("sportiq.core.value_bet._utcnow", lambda: datetime(2026, 1, 1, tzinfo=UTC))
