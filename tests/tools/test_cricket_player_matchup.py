"""Tool-layer tests for cricket_player_matchup (stubs chains, no live HTTP)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sportiq.core.errors import AllSourcesFailedError
from sportiq.cricket.intel_tools import cricket_player_matchup


def _mock_stats_result(
    name="Player A",
    role="batter",
    batting_avg=45.0,
    strike_rate=135.0,
    bowling_avg=None,
    source="cricapi",
) -> MagicMock:
    r = MagicMock()
    r.value = {
        "name": name,
        "role": role,
        "batting_avg": batting_avg,
        "strike_rate": strike_rate,
        "bowling_avg": bowling_avg,
        "economy_rate": None,
        "wickets": None,
    }
    r.source = source
    r.is_stale = False
    r.fallback_used = False
    r.data_age_seconds = 0
    r.duration_ms = 10
    return r


# --- INVALID_INPUT ---

async def test_invalid_same_player():
    result = await cricket_player_matchup("rohit_sharma", "rohit_sharma")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_invalid_blank_player_a():
    result = await cricket_player_matchup("", "bumrah")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_invalid_blank_player_b():
    result = await cricket_player_matchup("rohit", "")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_invalid_whitespace_player_a():
    result = await cricket_player_matchup("   ", "bumrah")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_player_identifiers_over_200_rejected_before_chain():
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock()
        result = await cricket_player_matchup("x" * 201, "bumrah")
        assert result["error"]["code"] == "INVALID_INPUT"
        mock_chain.fetch.assert_not_awaited()


async def test_same_player_trimmed_casefold_rejected_before_chain():
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock()
        result = await cricket_player_matchup("  Straße ", "STRASSE")
        assert result["error"]["code"] == "INVALID_INPUT"
        mock_chain.fetch.assert_not_awaited()


# --- ALL_SOURCES_FAILED ---

async def test_all_sources_failed_player_a():
    """If player_a fetch raises AllSourcesFailedError, return ALL_SOURCES_FAILED."""
    mock_b = _mock_stats_result("Bumrah", role="bowler", bowling_avg=22.0)
    exc = AllSourcesFailedError("upstream down", attempts=[])
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[exc, mock_b])
        result = await cricket_player_matchup("bad_id", "bumrah")
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_all_sources_failed_player_b():
    """If player_b fetch raises AllSourcesFailedError, return ALL_SOURCES_FAILED."""
    mock_a = _mock_stats_result("Rohit", role="batter", batting_avg=50.0)
    exc = AllSourcesFailedError("timeout", attempts=[])
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[mock_a, exc])
        result = await cricket_player_matchup("rohit", "bad_id")
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_player_matchup_unexpected_stats_error_reraises():
    mock_b = _mock_stats_result("Bumrah", role="bowler", bowling_avg=22.0)
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[TypeError("boom"), mock_b])
        with pytest.raises(TypeError, match="boom"):
            await cricket_player_matchup("bad_id", "bumrah")


# --- NOT_FOUND (genuinely unknown player, distinct from a source outage) ---

async def test_not_found_when_player_unknown():
    """A NotFoundError for either player yields NOT_FOUND, not ALL_SOURCES_FAILED."""
    from sportiq.core.errors import NotFoundError

    mock_b = _mock_stats_result("Bumrah", role="bowler", bowling_avg=22.0)
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[NotFoundError("no such player"), mock_b])
        result = await cricket_player_matchup("nonexistent_player", "bumrah")
    assert result["error"]["code"] == "NOT_FOUND"


async def test_all_sources_failed_propagates_attempts():
    mock_b = _mock_stats_result("Bumrah", role="bowler", bowling_avg=22.0)
    attempts = [{"name": "cricapi", "error": "timeout"}]
    exc = AllSourcesFailedError("upstream down", attempts=attempts)
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[exc, mock_b])
        result = await cricket_player_matchup("bad_id", "bumrah")
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"
    assert result["error"]["sources_tried"] == attempts


async def test_not_found_propagates_attempts():
    from sportiq.core.errors import NotFoundError

    mock_b = _mock_stats_result("Bumrah", role="bowler", bowling_avg=22.0)
    attempts = [{"name": "cricapi", "error": "not found"}]
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[NotFoundError("no such player", attempts=attempts), mock_b])
        result = await cricket_player_matchup("nonexistent_player", "bumrah")
    assert result["error"]["code"] == "NOT_FOUND"
    assert result["error"]["sources_tried"] == attempts



# --- valid path ---

async def test_valid_returns_envelope():
    mock_a = _mock_stats_result("Rohit Sharma", role="batter", batting_avg=45.0, strike_rate=135.0)
    mock_b = _mock_stats_result("Jasprit Bumrah", role="bowler", bowling_avg=22.0, source="cricapi")

    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[mock_a, mock_b])
        result = await cricket_player_matchup("rohit_sharma", "jasprit_bumrah")

    assert "data" in result
    assert "error" not in result
    assert "matchup_type" in result["data"]
    assert result["meta"]["estimated"] is True


async def test_valid_envelope_meta_source():
    mock_a = _mock_stats_result("A", role="batter", batting_avg=40.0, source="cricapi")
    mock_b = _mock_stats_result("B", role="bowler", bowling_avg=30.0, source="cricapi")

    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[mock_a, mock_b])
        result = await cricket_player_matchup("player_a", "player_b")

    assert result["meta"]["source"] == "cricapi"


async def test_valid_data_has_required_keys():
    mock_a = _mock_stats_result("A", role="batter", batting_avg=55.0, strike_rate=130.0)
    mock_b = _mock_stats_result("B", role="bowler", bowling_avg=25.0)

    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[mock_a, mock_b])
        result = await cricket_player_matchup("player_a", "player_b")

    data = result["data"]
    for key in ["matchup_type", "edge_holder", "edge_reason", "signals", "role_a", "role_b"]:
        assert key in data, f"missing key: {key}"


async def test_player_matchup_unwrapped_cricapi_cassette_shapes():
    """Unwrapped CricAPI cassette payloads yield non-other batter_vs_bowler matchup with signals."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parents[1] / "fixtures" / "cricapi" / "players_info.json"
    raw_fixture = json.loads(fixture_path.read_text())
    kohli_unwrapped = raw_fixture["data"]

    bumrah_unwrapped = {
        "id": "p_bumrah_001",
        "name": "Jasprit Bumrah",
        "country": "India",
        "playingRole": "Bowler",
        "stats": [
            {"fn": "bowling", "matchtype": "t20i", "stat": "Average", "value": "19.66"},
            {"fn": "bowling", "matchtype": "t20i", "stat": "Economy", "value": "6.55"},
            {"fn": "bowling", "matchtype": "t20i", "stat": "Wickets", "value": "74"},
        ],
    }

    r_a = MagicMock()
    r_a.value = kohli_unwrapped
    r_a.source = "cricapi"
    r_a.is_stale = False
    r_a.fallback_used = False
    r_a.data_age_seconds = 0
    r_a.duration_ms = 10

    r_b = MagicMock()
    r_b.value = bumrah_unwrapped
    r_b.source = "cricapi"
    r_b.is_stale = False
    r_b.fallback_used = False
    r_b.data_age_seconds = 0
    r_b.duration_ms = 10

    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[r_a, r_b])
        result = await cricket_player_matchup("p_kohli_001", "p_bumrah_001")

    assert "data" in result
    assert result["data"]["matchup_type"] == "batter_vs_bowler"
    assert result["data"]["edge_holder"] == "player_b"
    assert result["data"]["role_a"] == "Batter"
    assert result["data"]["role_b"] == "Bowler"
    assert result["data"]["signals"]["batting_avg_a"] == 51.39
    assert result["data"]["signals"]["strike_rate_a"] == 137.96
    assert result["data"]["signals"]["bowling_avg_b"] == 19.66
