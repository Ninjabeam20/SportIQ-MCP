"""Tool-layer tests for cricket_player_matchup (stubs chains, no live HTTP)."""

from unittest.mock import AsyncMock, MagicMock, patch

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
    """If player_a fetch raises, return ALL_SOURCES_FAILED."""
    mock_b = _mock_stats_result("Bumrah", role="bowler", bowling_avg=22.0)
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[Exception("upstream down"), mock_b])
        result = await cricket_player_matchup("bad_id", "bumrah")
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_all_sources_failed_player_b():
    """If player_b fetch raises, return ALL_SOURCES_FAILED."""
    mock_a = _mock_stats_result("Rohit", role="batter", batting_avg=50.0)
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[mock_a, Exception("timeout")])
        result = await cricket_player_matchup("rohit", "bad_id")
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# --- NOT_FOUND (genuinely unknown player, distinct from a source outage) ---

async def test_not_found_when_player_unknown():
    """A NotFoundError for either player yields NOT_FOUND, not ALL_SOURCES_FAILED."""
    from sportiq.core.errors import NotFoundError

    mock_b = _mock_stats_result("Bumrah", role="bowler", bowling_avg=22.0)
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=[NotFoundError("no such player"), mock_b])
        result = await cricket_player_matchup("nonexistent_player", "bumrah")
    assert result["error"]["code"] == "NOT_FOUND"


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
