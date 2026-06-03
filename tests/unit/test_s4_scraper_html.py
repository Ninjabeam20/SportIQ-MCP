"""S.4c — Assert scraper parse functions return text-only output (no raw HTML tags)."""
import re

from bs4 import BeautifulSoup

from sportiq.cricket.adapters.cricbuzz_scraper import _parse_live
from sportiq.cricket.adapters.ndtv_sports_scraper import _parse_live_matches, _parse_schedule

HTML_TAG_RE = re.compile(r"<[^>]+>")

_SAMPLE_NDTV_HTML = """
<html><body>
  <div class="match-card">India vs Australia <b>Live</b> - 145/3 (18.2)</div>
  <div class="match-card">England vs <script>alert('xss')</script>Pakistan</div>
</body></html>
"""

_SAMPLE_CRICBUZZ_HTML = """
<html><body>
  <div class="cb-mtch-lst">Ind vs Aus <style>.x{color:red}</style> Live</div>
</body></html>
"""

def test_ndtv_parse_live_no_html_tags():
    soup = BeautifulSoup(_SAMPLE_NDTV_HTML, "html.parser")
    matches = _parse_live_matches(soup)
    for m in matches:
        raw = m.get("raw", "")
        assert not HTML_TAG_RE.search(raw), f"Raw HTML found in NDTV output: {raw!r}"

def test_ndtv_parse_schedule_no_html_tags():
    soup = BeautifulSoup(_SAMPLE_NDTV_HTML, "html.parser")
    matches = _parse_schedule(soup)
    for m in matches:
        raw = m.get("raw", "")
        assert not HTML_TAG_RE.search(raw), f"Raw HTML found in NDTV schedule output: {raw!r}"

def test_cricbuzz_parse_live_no_html_tags():
    soup = BeautifulSoup(_SAMPLE_CRICBUZZ_HTML, "html.parser")
    matches = _parse_live(soup)
    for m in matches:
        raw = m.get("raw", "")
        assert not HTML_TAG_RE.search(raw), f"Raw HTML found in Cricbuzz output: {raw!r}"

def test_ndtv_parse_live_text_capped_at_200():
    long_text = "x" * 300
    html = f'<html><body><div class="match-card">{long_text}</div></body></html>'
    soup = BeautifulSoup(html, "html.parser")
    matches = _parse_live_matches(soup)
    for m in matches:
        assert len(m.get("raw", "")) <= 200

def test_truncate_payload_caps_list():
    from sportiq.core.tool_response import truncate_payload
    data = {"laps": list(range(300))}
    result, was_truncated = truncate_payload(data, "laps")
    assert was_truncated is True
    assert len(result["laps"]) == 200

def test_truncate_payload_no_truncation_needed():
    from sportiq.core.tool_response import truncate_payload
    data = {"laps": list(range(50))}
    result, was_truncated = truncate_payload(data, "laps")
    assert was_truncated is False
    assert len(result["laps"]) == 50
