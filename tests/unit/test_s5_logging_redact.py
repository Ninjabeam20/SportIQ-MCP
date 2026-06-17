"""S.5a — Assert structlog processor redacts secrets from all log events."""
from sportiq.core.logging import _gcp_severity_processor, _redact_event_processor


def test_redact_processor_scrubs_key_in_url():
    event = {
        "event": "fetch.url",
        "url": "https://api.cricapi.com/v1/matches?apikey=SECRET123&type=live",
    }
    result = _redact_event_processor(None, "info", event)
    assert "SECRET123" not in result["url"]
    assert "***" in result["url"]


def test_redact_processor_scrubs_authorization_header():
    event = {
        "event": "request.sent",
        "headers": "Authorization: Bearer MY_TOKEN_XYZ",
    }
    result = _redact_event_processor(None, "info", event)
    assert "MY_TOKEN_XYZ" not in result["headers"]
    assert "***" in result["headers"]


def test_redact_processor_leaves_non_secret_fields_intact():
    event = {
        "event": "chain.adapter.failed",
        "chain": "cricket:live_score",
        "adapter": "cricapi",
        "error": "timeout",
    }
    result = _redact_event_processor(None, "warning", event)
    assert result["chain"] == "cricket:live_score"
    assert result["adapter"] == "cricapi"
    assert result["error"] == "timeout"


def test_redact_processor_handles_non_string_values():
    event = {
        "event": "cache.hit",
        "age_seconds": 45,
        "is_stale": False,
    }
    result = _redact_event_processor(None, "info", event)
    assert result["age_seconds"] == 45
    assert result["is_stale"] is False


def test_redact_processor_scrubs_known_credential_value(monkeypatch):
    from sportiq import config as config_module

    monkeypatch.setattr(config_module.settings, "cricapi_key", "LIVE_KEY_ABCDEF")
    event = {
        "event": "adapter.response",
        "url": "https://api.cricapi.com/v1/matches?apikey=LIVE_KEY_ABCDEF",
    }
    result = _redact_event_processor(None, "info", event)
    assert "LIVE_KEY_ABCDEF" not in result["url"]


def test_gcp_severity_maps_level_to_cloud_logging_severity():
    assert _gcp_severity_processor(None, "error", {"level": "error"})["severity"] == "ERROR"
    assert _gcp_severity_processor(None, "warning", {"level": "warning"})["severity"] == "WARNING"
    assert _gcp_severity_processor(None, "info", {"level": "info"})["severity"] == "INFO"


def test_gcp_severity_noop_when_no_level():
    assert "severity" not in _gcp_severity_processor(None, "info", {"event": "x"})
