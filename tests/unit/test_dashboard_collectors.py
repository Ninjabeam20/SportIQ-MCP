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


def test_github_token_reads_dotenv_before_gh(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=ghp_test_not_real\n")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(dashboard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        dashboard.subprocess,
        "check_output",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("gh should not run")),
    )
    assert dashboard._github_token() == "ghp_test_not_real"


def test_home_server_filters_healthcheck_get(tmp_path, monkeypatch):
    jsonl = tmp_path / "events.jsonl"
    jsonl.write_text(
        "\n".join(
            [
                '{"event":"mcp_request","method":"GET","user_agent":"Python-urllib/3.11","timestamp":"2026-09-02T12:00:00+00:00"}',
                '{"event":"mcp_request","method":"POST","client_name":"claude","user_agent":"claude","timestamp":"2026-09-02T12:01:00+00:00"}',
                '{"event":"tool_call","tool":"sportiq_health","success":true,"latency_ms":12.5,"client_name":"claude","timestamp":"2026-09-02T12:01:01+00:00"}',
                '{"event":"cache.hit","timestamp":"2026-09-02T12:01:02+00:00"}',
            ]
        )
        + "\n"
    )
    monkeypatch.setattr(dashboard, "ARCHIVE_DIR", tmp_path)
    monkeypatch.setenv("SPORTIQ_HOME_JSONL", str(jsonl))
    result = dashboard.collect_home_server()
    assert result["present"] is True
    assert result["health_filtered"] == 1
    assert result["http_kept"] == 1
    assert result["total_calls"] == 1
    assert result["total_ok"] == 1
    assert result["tools"][0]["tool"] == "sportiq_health"


def test_home_server_missing_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.delenv("SPORTIQ_HOME_JSONL", raising=False)
    monkeypatch.setattr(dashboard, "ARCHIVE_DIR", tmp_path)
    result = dashboard.collect_home_server()
    assert result["present"] is False
    assert result["total_calls"] == 0


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
