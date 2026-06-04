"""Tests for the shared paginate() helper and tool-level pagination."""
from unittest.mock import AsyncMock, MagicMock, patch

from sportiq.core.tool_response import paginate


def test_paginate_first_page_has_more():
    data = {"items": list(range(10))}
    out = paginate(data, "items", limit=4, offset=0)
    assert out["items"] == [0, 1, 2, 3]
    p = out["pagination"]
    assert p == {"total": 10, "count": 4, "offset": 0, "limit": 4, "has_more": True, "next_offset": 4}


def test_paginate_last_page_no_more():
    data = {"items": list(range(10))}
    out = paginate(data, "items", limit=4, offset=8)
    assert out["items"] == [8, 9]
    p = out["pagination"]
    assert p["has_more"] is False
    assert p["next_offset"] is None
    assert p["count"] == 2


def test_paginate_offset_past_end_empty():
    data = {"items": [1, 2, 3]}
    out = paginate(data, "items", limit=5, offset=99)
    assert out["items"] == []
    assert out["pagination"]["has_more"] is False


def test_paginate_missing_key_treated_as_empty():
    out = paginate({}, "items", limit=5, offset=0)
    assert out["items"] == []
    assert out["pagination"]["total"] == 0


async def test_schedule_paginates_and_reports_metadata():
    from sportiq.cricket import tools

    mock_result = MagicMock()
    mock_result.value = {"matches": [{"id": f"m{i}"} for i in range(7)]}
    mock_result.source = "cricapi"
    mock_result.is_stale = False
    mock_result.fallback_used = False
    mock_result.data_age_seconds = 0
    mock_result.duration_ms = 1

    with patch("sportiq.cricket.tools.fixtures_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        resp = await tools.cricket_get_schedule(limit=3, offset=3)

    assert [m["id"] for m in resp["data"]["matches"]] == ["m3", "m4", "m5"]
    assert resp["data"]["pagination"]["next_offset"] == 6
    assert resp["data"]["pagination"]["total"] == 7


async def test_schedule_rejects_bad_limit():
    from sportiq.cricket import tools

    resp = await tools.cricket_get_schedule(limit=0)
    assert resp["error"]["code"] == "INVALID_INPUT"
