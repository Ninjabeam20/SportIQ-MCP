"""S.3 — Input validation sweep + cache-key injection hardening tests.

S.3a: Length-cap tests — call tools directly with oversized strings and assert
      INVALID_INPUT is returned (no HTTP needed; chains are never reached).

S.3b: Cache-key injection tests — call chain.cache_key_fn directly with strings
      containing ':' and '*' and assert the output key does not carry the raw
      special characters from the input.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LONG_100 = "x" * 101   # one over the 100-char cap
_LONG_200 = "y" * 201   # one over the 200-char cap


def _is_invalid_input(resp: dict) -> bool:
    return resp.get("error", {}).get("code") == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# S.3a — cricket/tools.py length caps
# ---------------------------------------------------------------------------


async def test_cricket_get_scorecard_match_id_too_long():
    from sportiq.cricket.tools import cricket_get_scorecard

    resp = await cricket_get_scorecard(match_id=_LONG_100)
    assert _is_invalid_input(resp), resp
    assert "100" in resp["error"]["message"]


async def test_cricket_get_points_table_series_id_too_long():
    from sportiq.cricket.tools import cricket_get_points_table

    resp = await cricket_get_points_table(series_id=_LONG_100)
    assert _is_invalid_input(resp), resp
    assert "100" in resp["error"]["message"]


async def test_cricket_get_squad_team_too_long():
    from sportiq.cricket.tools import cricket_get_squad

    resp = await cricket_get_squad(team=_LONG_100)
    assert _is_invalid_input(resp), resp
    assert "100" in resp["error"]["message"]


# ---------------------------------------------------------------------------
# S.3a — cricket/intel_tools.py length caps
# ---------------------------------------------------------------------------


async def test_cricket_build_dream11_team_a_too_long():
    from sportiq.cricket.intel_tools import cricket_build_dream11_team

    resp = await cricket_build_dream11_team(team_a=_LONG_100, team_b="CSK", venue="wankhede")
    assert _is_invalid_input(resp), resp
    assert "team_a" in resp["error"]["message"]


async def test_cricket_build_dream11_team_b_too_long():
    from sportiq.cricket.intel_tools import cricket_build_dream11_team

    resp = await cricket_build_dream11_team(team_a="MI", team_b=_LONG_100, venue="wankhede")
    assert _is_invalid_input(resp), resp
    assert "team_b" in resp["error"]["message"]


async def test_cricket_build_dream11_venue_too_long():
    from sportiq.cricket.intel_tools import cricket_build_dream11_team

    resp = await cricket_build_dream11_team(team_a="MI", team_b="CSK", venue=_LONG_200)
    assert _is_invalid_input(resp), resp
    assert "venue" in resp["error"]["message"]


async def test_cricket_captain_recommendation_team_a_too_long():
    from sportiq.cricket.intel_tools import cricket_captain_recommendation

    resp = await cricket_captain_recommendation(team_a=_LONG_100, team_b="CSK", venue="wankhede")
    assert _is_invalid_input(resp), resp
    assert "team_a" in resp["error"]["message"]


async def test_cricket_captain_recommendation_team_b_too_long():
    from sportiq.cricket.intel_tools import cricket_captain_recommendation

    resp = await cricket_captain_recommendation(team_a="MI", team_b=_LONG_100, venue="wankhede")
    assert _is_invalid_input(resp), resp
    assert "team_b" in resp["error"]["message"]


async def test_cricket_captain_recommendation_venue_too_long():
    from sportiq.cricket.intel_tools import cricket_captain_recommendation

    resp = await cricket_captain_recommendation(team_a="MI", team_b="CSK", venue=_LONG_200)
    assert _is_invalid_input(resp), resp
    assert "venue" in resp["error"]["message"]


async def test_cricket_differential_picks_team_a_too_long():
    from sportiq.cricket.intel_tools import cricket_differential_picks

    resp = await cricket_differential_picks(team_a=_LONG_100, team_b="CSK", venue="wankhede")
    assert _is_invalid_input(resp), resp
    assert "team_a" in resp["error"]["message"]


async def test_cricket_differential_picks_team_b_too_long():
    from sportiq.cricket.intel_tools import cricket_differential_picks

    resp = await cricket_differential_picks(team_a="MI", team_b=_LONG_100, venue="wankhede")
    assert _is_invalid_input(resp), resp
    assert "team_b" in resp["error"]["message"]


async def test_cricket_differential_picks_venue_too_long():
    from sportiq.cricket.intel_tools import cricket_differential_picks

    resp = await cricket_differential_picks(team_a="MI", team_b="CSK", venue=_LONG_200)
    assert _is_invalid_input(resp), resp
    assert "venue" in resp["error"]["message"]


async def test_cricket_differential_picks_ownership_threshold_below_zero():
    from sportiq.cricket.intel_tools import cricket_differential_picks

    resp = await cricket_differential_picks(
        team_a="MI", team_b="CSK", venue="wankhede", ownership_threshold=-1
    )
    assert _is_invalid_input(resp), resp
    assert "ownership_threshold" in resp["error"]["message"]


async def test_cricket_differential_picks_ownership_threshold_above_100():
    from sportiq.cricket.intel_tools import cricket_differential_picks

    resp = await cricket_differential_picks(
        team_a="MI", team_b="CSK", venue="wankhede", ownership_threshold=101
    )
    assert _is_invalid_input(resp), resp
    assert "ownership_threshold" in resp["error"]["message"]


async def test_cricket_get_pitch_report_venue_too_long():
    from sportiq.cricket.intel_tools import cricket_get_pitch_report

    resp = await cricket_get_pitch_report(venue=_LONG_200)
    assert _is_invalid_input(resp), resp
    assert "venue" in resp["error"]["message"]


# ---------------------------------------------------------------------------
# S.3a — football/tools.py length caps
# ---------------------------------------------------------------------------


async def test_football_get_squad_team_too_long():
    from sportiq.football.tools import football_get_squad

    resp = await football_get_squad(team=_LONG_100)
    assert _is_invalid_input(resp), resp
    assert "100" in resp["error"]["message"]


# ---------------------------------------------------------------------------
# S.3a — football/intel_tools.py length caps
# ---------------------------------------------------------------------------


async def test_football_xg_model_home_team_too_long():
    from unittest.mock import AsyncMock, patch

    from sportiq.core.fallback import FallbackResult
    from sportiq.football.intel_tools import football_xg_model

    mock_result = FallbackResult(
        value={"ratings": {"ARG": 1820, "BRA": 1810}, "groups": {}, "teams": {}},
        source="static_seed",
        is_stale=False,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )
    with patch("sportiq.football.intel_tools.football_groups_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        resp = await football_xg_model(home_team=_LONG_100, away_team="BRA")
    assert _is_invalid_input(resp), resp
    assert "home_team" in resp["error"]["message"]


async def test_football_xg_model_away_team_too_long():
    from unittest.mock import AsyncMock, patch

    from sportiq.core.fallback import FallbackResult
    from sportiq.football.intel_tools import football_xg_model

    mock_result = FallbackResult(
        value={"ratings": {"ARG": 1820, "BRA": 1810}, "groups": {}, "teams": {}},
        source="static_seed",
        is_stale=False,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )
    with patch("sportiq.football.intel_tools.football_groups_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        resp = await football_xg_model(home_team="ARG", away_team=_LONG_100)
    assert _is_invalid_input(resp), resp
    assert "away_team" in resp["error"]["message"]


async def test_football_match_predictor_home_team_too_long():
    from unittest.mock import AsyncMock, patch

    from sportiq.core.fallback import FallbackResult
    from sportiq.football.intel_tools import football_match_predictor

    mock_result = FallbackResult(
        value={"ratings": {"ARG": 1820, "BRA": 1810}, "groups": {}, "teams": {}},
        source="static_seed",
        is_stale=False,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )
    with patch("sportiq.football.intel_tools.football_groups_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        resp = await football_match_predictor(home_team=_LONG_100, away_team="BRA")
    assert _is_invalid_input(resp), resp
    assert "home_team" in resp["error"]["message"]


async def test_football_match_predictor_away_team_too_long():
    from unittest.mock import AsyncMock, patch

    from sportiq.core.fallback import FallbackResult
    from sportiq.football.intel_tools import football_match_predictor

    mock_result = FallbackResult(
        value={"ratings": {"ARG": 1820, "BRA": 1810}, "groups": {}, "teams": {}},
        source="static_seed",
        is_stale=False,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )
    with patch("sportiq.football.intel_tools.football_groups_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        resp = await football_match_predictor(home_team="ARG", away_team=_LONG_100)
    assert _is_invalid_input(resp), resp
    assert "away_team" in resp["error"]["message"]


async def test_football_knockout_path_team_too_long():
    from unittest.mock import AsyncMock, patch

    from sportiq.core.fallback import FallbackResult
    from sportiq.football.intel_tools import football_knockout_path

    mock_result = FallbackResult(
        value={"ratings": {"FRA": 1850}, "groups": {}, "teams": {}},
        source="static_seed",
        is_stale=False,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )
    with patch("sportiq.football.intel_tools.football_groups_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=mock_result)
        resp = await football_knockout_path(team=_LONG_100)
    assert _is_invalid_input(resp), resp
    assert "team" in resp["error"]["message"]


# ---------------------------------------------------------------------------
# S.3b — Cache-key injection hardening
# Verify that free-text user strings containing ':' or '*' do NOT appear raw
# in the generated cache key.
# ---------------------------------------------------------------------------


def test_pitch_data_cache_key_no_raw_colon():
    from sportiq.cricket.chains import pitch_data_chain

    key = pitch_data_chain.cache_key_fn(venue="malicious:venue*name")
    # The key must start with the static prefix
    assert key.startswith("sportiq:cricket:pitch:")
    # The raw user input must NOT appear in the key suffix
    suffix = key[len("sportiq:cricket:pitch:"):]
    assert ":" not in suffix, f"raw colon leaked into key suffix: {key!r}"
    assert "*" not in suffix, f"raw star leaked into key suffix: {key!r}"


def test_squad_cache_key_no_raw_colon():
    from sportiq.cricket.chains import squad_chain

    key = squad_chain.cache_key_fn(team="Mumbai:Indians*", series_id=None)
    assert key.startswith("sportiq:cricket:squad:")
    parts = key.split(":")
    # parts: ['sportiq', 'cricket', 'squad', <hash>, <series>]
    assert len(parts) == 5, f"unexpected key structure: {key!r}"
    team_hash = parts[3]
    assert ":" not in team_hash, f"raw colon in team hash: {key!r}"
    assert "*" not in team_hash, f"raw star in team hash: {key!r}"


def test_football_squad_cache_key_no_raw_colon():
    from sportiq.football.chains import football_squad_chain

    key = football_squad_chain.cache_key_fn(team="Arg:entina*")
    assert key.startswith("sportiq:football:squad:")
    suffix = key[len("sportiq:football:squad:"):]
    assert ":" not in suffix, f"raw colon leaked into key suffix: {key!r}"
    assert "*" not in suffix, f"raw star leaked into key suffix: {key!r}"


def test_f1_sessions_cache_key_no_raw_colon_with_country():
    from sportiq.f1.chains import f1_sessions_chain

    key = f1_sessions_chain.cache_key_fn(year=2025, country="Great:Britain*")
    assert key.startswith("sportiq:f1:sessions:2025:")
    suffix = key[len("sportiq:f1:sessions:2025:"):]
    assert ":" not in suffix, f"raw colon leaked into key suffix: {key!r}"
    assert "*" not in suffix, f"raw star leaked into key suffix: {key!r}"


def test_f1_sessions_cache_key_no_country_gives_all():
    from sportiq.f1.chains import f1_sessions_chain

    key = f1_sessions_chain.cache_key_fn(year=2025, country=None)
    assert key == "sportiq:f1:sessions:2025:all"


def test_squad_cache_key_consistent_for_same_team():
    """Same team name must hash to the same key (determinism)."""
    from sportiq.cricket.chains import squad_chain

    k1 = squad_chain.cache_key_fn(team="Mumbai Indians", series_id="ipl2026")
    k2 = squad_chain.cache_key_fn(team="Mumbai Indians", series_id="ipl2026")
    assert k1 == k2


def test_pitch_data_cache_key_consistent_for_same_venue():
    """Same venue must hash to the same key (determinism)."""
    from sportiq.cricket.chains import pitch_data_chain

    k1 = pitch_data_chain.cache_key_fn(venue="Wankhede Stadium")
    k2 = pitch_data_chain.cache_key_fn(venue="Wankhede Stadium")
    assert k1 == k2
