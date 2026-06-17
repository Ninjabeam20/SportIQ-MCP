"""Unit tests for the local analytics dashboard (scripts/dashboard.py).

No live HTTP, no GCP calls. Verifies the User-Agent classifier and the
degrade-don't-crash contract of the _collect wrapper.
"""

import importlib.util
from pathlib import Path

import pytest

# scripts/ is not a package; load the module by path.
_SPEC = importlib.util.spec_from_file_location(
    "dashboard",
    Path(__file__).resolve().parents[2] / "scripts" / "dashboard.py",
)
dashboard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dashboard)


@pytest.mark.parametrize(
    "ua, expected",
    [
        ("claude-ai/1.0", "Claude"),
        ("ChatGPT-User/2.0", "ChatGPT"),
        ("Cursor/0.4 (darwin)", "Cursor"),
        ("python-httpx/0.27.0", "python-httpx"),
        ("", "unknown"),
        ("Mozilla/5.0 something-weird", "other"),
    ],
)
def test_classify_user_agent(ua, expected):
    assert dashboard.classify_user_agent(ua) == expected


def test_collect_falls_back_to_cache_on_failure(tmp_path, monkeypatch):
    """A collector that raises must not crash — it returns cached/empty."""
    monkeypatch.setattr(dashboard, "CACHE_DIR", tmp_path)

    def boom():
        raise RuntimeError("upstream down")

    result = dashboard._collect("github", boom)
    assert result["_unavailable"] is True
    assert "RuntimeError: upstream down" in result["_error"]


def test_collect_writes_and_reads_cache(tmp_path, monkeypatch):
    """A successful collect caches; a later failure serves that cache."""
    monkeypatch.setattr(dashboard, "CACHE_DIR", tmp_path)

    ok = dashboard._collect("github", lambda: {"stars": 42})
    assert ok["stars"] == 42 and ok["_from_cache"] is False

    def boom():
        raise ValueError("nope")

    fallback = dashboard._collect("github", boom)
    assert fallback["stars"] == 42 and fallback["_from_cache"] is True
    assert "ValueError: nope" in fallback["_error"]
