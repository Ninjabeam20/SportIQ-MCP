"""Tool-layer tests for cricket_head_to_head (stubs chains, no live HTTP)."""

from unittest.mock import AsyncMock, MagicMock, patch

from sportiq.cricket.intel_tools import cricket_head_to_head


def _mock_squad_result(players: list[dict], source: str = "static_seed") -> MagicMock:
    r = MagicMock()
    r.value = {"players": players}
    r.source = source
    r.is_stale = False
    r.fallback_used = False
    r.data_age_seconds = 0
    r.duration_ms = 5
    return r


async def test_same_team_invalid():
    result = await cricket_head_to_head("MI", "MI")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_same_team_case_insensitive():
    result = await cricket_head_to_head("mi", "MI")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_empty_team_a_invalid():
    result = await cricket_head_to_head("", "CSK")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_empty_team_b_invalid():
    result = await cricket_head_to_head("MI", "")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_whitespace_only_team_invalid():
    result = await cricket_head_to_head("  ", "CSK")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_valid_returns_envelope():
    mock_squad = _mock_squad_result([{"name": "P1", "player_id": "1"}])

    with patch("sportiq.cricket.intel_tools.squad_chain") as ms, \
         patch("sportiq.cricket.intel_tools.player_stats_chain") as mps:
        ms.fetch = AsyncMock(return_value=mock_squad)
        mps.fetch = AsyncMock(side_effect=Exception("no stats"))
        result = await cricket_head_to_head("MI", "CSK")

    assert "data" in result
    assert "error" not in result
    assert result["meta"]["estimated"] is True


async def test_data_has_required_keys():
    mock_squad = _mock_squad_result([{"name": "P1", "player_id": "1"}])

    with patch("sportiq.cricket.intel_tools.squad_chain") as ms, \
         patch("sportiq.cricket.intel_tools.player_stats_chain") as mps:
        ms.fetch = AsyncMock(return_value=mock_squad)
        mps.fetch = AsyncMock(side_effect=Exception("no stats"))
        result = await cricket_head_to_head("MI", "CSK")

    for key in [
        "team_a", "team_b",
        "team_a_edge_count", "team_b_edge_count",
        "key_players_a", "key_players_b",
        "h2h_win_rate_a", "h2h_win_rate_b",
        "win_prob_a", "win_prob_b",
    ]:
        assert key in result["data"], f"missing key: {key}"


async def test_win_prob_present_and_sums_to_one():
    mock_squad = _mock_squad_result([{"name": "P1"}])

    with patch("sportiq.cricket.intel_tools.squad_chain") as ms, \
         patch("sportiq.cricket.intel_tools.player_stats_chain") as mps:
        ms.fetch = AsyncMock(return_value=mock_squad)
        mps.fetch = AsyncMock(side_effect=Exception("no stats"))
        result = await cricket_head_to_head("India", "Australia")

    data = result["data"]
    assert abs(data["win_prob_a"] + data["win_prob_b"] - 1.0) < 0.001


async def test_squad_failure_returns_all_sources_failed():
    from sportiq.core.errors import AllSourcesFailedError

    with patch("sportiq.cricket.intel_tools.squad_chain") as ms:
        ms.fetch = AsyncMock(side_effect=AllSourcesFailedError("no squads", attempts=[]))
        result = await cricket_head_to_head("MI", "CSK")

    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_no_player_ids_gives_neutral_result():
    """Squads with no player_id still produce a valid envelope (all form_score=50)."""
    mock_squad_a = _mock_squad_result([{"name": "P1"}, {"name": "P2"}])
    mock_squad_b = _mock_squad_result([{"name": "Q1"}, {"name": "Q2"}])

    with patch("sportiq.cricket.intel_tools.squad_chain") as ms:
        ms.fetch = AsyncMock(side_effect=[mock_squad_a, mock_squad_b])
        result = await cricket_head_to_head("MI", "CSK")

    assert "data" in result
    # All neutral → equal h2h rates
    data = result["data"]
    assert data["h2h_win_rate_a"] == data["h2h_win_rate_b"]


async def test_meta_estimated_true():
    mock_squad = _mock_squad_result([])

    with patch("sportiq.cricket.intel_tools.squad_chain") as ms:
        ms.fetch = AsyncMock(return_value=mock_squad)
        result = await cricket_head_to_head("MI", "CSK")

    assert result["meta"]["estimated"] is True
