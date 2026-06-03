"""Redaction guard — secrets must never survive scrub()."""
from __future__ import annotations

import pytest

from sportiq.core.redact import REDACTED, scrub


def test_scrub_redacts_lowercase_apikey_query_param():
    url = "https://api.cricapi.com/v1/currentMatches?apikey=SECRET123&offset=0"
    out = scrub(url)
    assert "SECRET123" not in out
    assert "offset=0" in out  # non-secret params survive


def test_scrub_redacts_camelcase_apikey_query_param():
    url = "https://api.the-odds-api.com/v4/sports?apiKey=ODDSKEY&regions=uk"
    out = scrub(url)
    assert "ODDSKEY" not in out
    assert REDACTED in out
    assert "regions=uk" in out


def test_scrub_redacts_authorization_bearer_header():
    text = "request failed Authorization: Bearer abc.def.ghi"
    out = scrub(text)
    assert "abc.def.ghi" not in out


def test_scrub_redacts_rapidapi_key_header():
    text = "headers={'x-rapidapi-key': 'RAPIDSECRET'}"
    out = scrub(text)
    assert "RAPIDSECRET" not in out


def test_scrub_redacts_known_credential_value_anywhere(monkeypatch):
    from sportiq import config as config_module

    monkeypatch.setattr(config_module.settings, "cricapi_key", "LIVEKEYVALUE")
    # Even outside a query-param shape, the literal value is caught.
    out = scrub("boom while calling upstream with LIVEKEYVALUE embedded")
    assert "LIVEKEYVALUE" not in out
    assert REDACTED in out


def test_scrub_leaves_clean_text_unchanged():
    text = "HTTPStatusError: 500 Server Error for url 'https://openf1.org/v1/laps?session_key=9877'"
    assert scrub(text) == text


@pytest.mark.parametrize("value", ["", None])
def test_scrub_handles_empty(value):
    assert scrub(value) == value
