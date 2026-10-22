"""Local dashboard regressions: overlapping archives, honest metrics, offline safety."""

import importlib.util
import json
from pathlib import Path

import httpx
import pytest


@pytest.fixture
def dashboard():
    path = Path(__file__).resolve().parents[2] / "scripts/dashboard_live.py"
    assert path.exists(), "The separate live dashboard has not been implemented"
    spec = importlib.util.spec_from_file_location("dashboard_live", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_merge_events_deduplicates_snapshots_preserving_same_file_multiplicity(dashboard, tmp_path):
    event = {
        "event": "tool_call",
        "timestamp": "2026-09-01T10:00:00Z",
        "tool": "football_get_groups",
        "success": True,
        "latency_ms": 10,
    }
    one, two = tmp_path / "one.jsonl", tmp_path / "two.jsonl"
    one.write_text(json.dumps(event) + "\n" + json.dumps(event) + "\n")
    two.write_text(json.dumps(event) + "\n")
    rows, invalid = dashboard.read_events([one, two], "dell")
    assert len(rows) == 2
    assert invalid == 0


def test_merge_events_handles_archive_shape_and_invalid_lines(dashboard, tmp_path):
    path = tmp_path / "calls.jsonl"
    path.write_text(
        '{"ts":"2026-08-01T10:00:00+00:00","tool":"f1_get_drivers",'
        '"client":"Claude","success":false,"latency_ms":20}\n'
        "broken\n[]\n"
    )
    rows, invalid = dashboard.read_events([path], "gcp")
    assert len(rows) == 1
    assert rows[0]["client"] == "Claude"
    assert rows[0]["era"] == "gcp"
    assert rows[0]["event"] == "tool_call"
    assert invalid == 2


def test_event_union_refines_client_label_without_double_counting(dashboard, tmp_path):
    raw = tmp_path / "raw.jsonl"
    retained = tmp_path / "retained.jsonl"
    event = {
        "event": "tool_call",
        "timestamp": "2026-10-01T01:00:00Z",
        "tool": "football_get_groups",
        "success": True,
    }
    raw.write_text(
        json.dumps({**event, "user_agent": "BrickBlueBot/0.1 (+https://brick.blue/bot)"}) + "\n"
    )
    retained.write_text(json.dumps({**event, "client": "other"}) + "\n")
    rows, _ = dashboard.read_events([raw, retained], "dell")
    assert len(rows) == 1
    assert rows[0]["client"] == "BrickBlueBot"


def test_daily_merge_replaces_overlap_and_keeps_unobserved_gap(dashboard):
    result = dashboard.merge_daily(
        [
            {"days": ["2026-08-01", "2026-08-02"], "downloads": [3, 4]},
            {"days": ["2026-08-02", "2026-08-04"], "downloads": [5, 7]},
        ],
        "downloads",
    )
    assert result == {"2026-08-01": 3, "2026-08-02": 5, "2026-08-04": 7}


def test_tool_summary_separates_http_gets_and_missing_latency(dashboard):
    rows = [
        {"event": "mcp_request", "method": "GET", "ts": "2026-09-01T01:00:00Z"},
        {"event": "mcp_request", "method": "POST", "ts": "2026-09-01T01:00:01Z"},
        {"event": "tool_call", "tool": "sportiq_health", "success": True},
        {"event": "tool_call", "tool": "football_get_groups", "success": True},
        {
            "event": "tool_call",
            "tool": "f1_get_drivers",
            "success": False,
            "latency_ms": 6000,
            "error": "ALL_SOURCES_FAILED",
        },
    ]
    summary = dashboard.summarize(rows)
    assert summary["total_calls"] == 2
    assert summary["health_calls"] == 1
    assert summary["http_get"] == 1
    assert summary["http_other"] == 1
    assert summary["errors"] == 1
    assert summary["latency_samples"] == 1
    assert summary["p95_ms"] == 6000
    assert summary["slow_5s"] == 1
    assert summary["tools"][0]["avg_ms"] is None


def test_empty_summary_does_not_claim_measured_zero_latency(dashboard):
    summary = dashboard.summarize([])
    assert summary["p50_ms"] is None
    assert summary["error_rate"] is None


def test_source_failure_retains_last_success_and_marks_stale(dashboard, tmp_path):
    cache = tmp_path / "github.json"
    cache.write_text('{"stars":7,"_cached_at":"2026-01-01T00:00:00+00:00"}')

    def fail():
        raise RuntimeError("failed")

    result = dashboard.collect_cached(tmp_path, "github", fail, 60, online=True)
    assert result["stars"] == 7
    assert result["_state"] == "stale"
    assert result["_cached_at"] == "2026-01-01T00:00:00+00:00"
    assert json.loads(cache.read_text())["stars"] == 7
    # An unavailable service should not be retried on every page refresh.
    second = dashboard.collect_cached(tmp_path, "github", lambda: {"stars": 99}, 60, online=True)
    assert second["stars"] == 7
    assert second["_state"] == "stale"


def test_offline_build_preserves_originals_and_labels_unavailable(dashboard, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard, "ROOT", tmp_path)
    (tmp_path / ".dashboard_cache").mkdir()
    original = tmp_path / "dashboard.html"
    original.write_text("historical dashboard")
    cache = tmp_path / ".dashboard_cache/cloud_run.json"
    cache.write_text('{"total_requests":123,"_cached_at":"2026-09-02T00:00:00Z"}')
    data = dashboard.build(online=False)
    assert data["gcp"]["total_requests"] == 123
    assert data["gcp"]["_state"] == "archive"
    assert data["cloudflare"]["_state"] == "unavailable"
    assert data["dell"]["_state"] == "unavailable"
    assert original.read_text() == "historical dashboard"
    assert json.loads(cache.read_text())["total_requests"] == 123


def test_render_escapes_script_termination(dashboard, tmp_path):
    template = tmp_path / "template.html"
    output = tmp_path / "new.html"
    template.write_text("<script>const DATA=__DATA__;</script>")
    dashboard.render({"name": "</script><script>alert(1)</script>"}, output, template)
    assert output.read_text().count("</script>") == 1


def test_github_uses_canonical_repo_url_without_trailing_slash(dashboard, monkeypatch, respx_mock):
    fixture = Path(__file__).resolve().parents[1] / "fixtures/dashboard_live/github_repo.json"
    root = "https://api.github.com/repos/Ninjabeam20/SportIQ-MCP"
    respx_mock.get(root).mock(
        return_value=httpx.Response(200, json=json.loads(fixture.read_text()))
    )
    respx_mock.get(url__regex=root + r"/.*").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    monkeypatch.setattr(
        dashboard,
        "legacy",
        lambda: type("Legacy", (), {"_github_token": staticmethod(lambda: None)})(),
    )
    result = dashboard.collect_github()
    assert result["forks"] == 1
    assert result["stars"] == 10
    assert result["endpoint_errors"]["views"] == "HTTP 404"
