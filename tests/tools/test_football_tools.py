"""Football tool tests — chains stubbed, envelope shape + error codes asserted."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.fallback import FallbackResult
from sportiq.football.adapters.static_seed import load_elo_seed, load_wc2026


def _fr(value, source="static_seed", is_stale=False):
    return FallbackResult(
        value=value,
        source=source,
        is_stale=is_stale,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )


def _draw_payload() -> dict:
    wc = load_wc2026()
    return {
        "groups": wc["groups"],
        "format": wc["format"],
        "teams": wc["teams"],
        "ratings": load_elo_seed(),
        "source": "static_seed",
    }


# -- RAW tools -----------------------------------------------------------------


async def test_get_groups_returns_envelope():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await tools.football_get_groups()
    assert "data" in result and "meta" in result
    assert len(result["data"]["groups"]) == 12


async def test_get_fixtures_all_sources_failed():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_fixtures_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.football_get_fixtures()
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_get_fixtures_not_found_returns_envelope():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_fixtures_chain") as mock:
        mock.fetch = AsyncMock(side_effect=NotFoundError("missing"))
        result = await tools.football_get_fixtures()
    assert result["error"]["code"] == "NOT_FOUND"


async def test_get_squad_empty_team_invalid_input():
    from sportiq.football import tools

    result = await tools.football_get_squad(team="  ")
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_get_squad_no_key_serves_static_seed(monkeypatch):
    # A1: default offline path — api_football raises MissingCredentialsError, so
    # the real chain serves the static seed (empty-but-valid squad).
    from sportiq.config import settings
    from sportiq.football import tools

    monkeypatch.setattr(settings, "apifootball_key", None)
    result = await tools.football_get_squad(team="ARG")
    assert result["meta"]["source"] == "static_seed"
    assert result["data"]["team"] == "ARG"


async def test_get_match_stats_invalid_team_id():
    from sportiq.football import tools

    result = await tools.football_get_match_stats(team=0)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_get_match_stats_all_sources_failed():
    # A2: network-only tool, no static terminator. When the chain exhausts both
    # network adapters the tool returns a clean error envelope, no crash.
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_team_stats_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.football_get_match_stats(team=26)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_get_standings_surfaces_is_stale():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_standings_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr({"standings": []}, source="cache:stale", is_stale=True))
        result = await tools.football_get_standings()
    assert result["meta"]["is_stale"] is True


# -- INTEL tools ---------------------------------------------------------------


async def test_xg_model_returns_probabilities():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_xg_model(home_team="ARG", away_team="USA")
    data = result["data"]
    assert abs(data["home_win"] + data["draw"] + data["away_win"] - 1.0) < 1e-6
    assert result["meta"]["estimated"] is True
    assert "is_stale" in result["meta"]


async def test_xg_model_unknown_team_not_found():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_xg_model(home_team="ZZZ", away_team="ARG")
    assert result["error"]["code"] == "NOT_FOUND"


async def test_matchup_validation_rejects_blank_and_same_before_chain():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock()
        for fn in (intel_tools.football_xg_model, intel_tools.football_match_predictor):
            blank = await fn(home_team="  ", away_team="ARG")
            same = await fn(home_team=" arg ", away_team="ARG")
            assert blank["error"]["code"] == "INVALID_INPUT"
            assert same["error"]["code"] == "INVALID_INPUT"
        mock.fetch.assert_not_awaited()


async def test_xg_model_chain_not_found_returns_envelope():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(side_effect=NotFoundError("missing"))
        result = await intel_tools.football_xg_model(home_team="ARG", away_team="USA")
    assert result["error"]["code"] == "NOT_FOUND"


async def test_match_predictor_returns_scoreline():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_match_predictor(home_team="BRA", away_team="QAT")
    assert "-" in result["data"]["most_likely_score"]
    assert result["data"]["predicted_winner"] in {"BRA", "QAT", "DRAW"}


async def test_simulate_group_models_contextual_best_third_advancement():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as gmock, \
         patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock:
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        result = await intel_tools.football_simulate_group(group="A", iterations=1500)
    teams = result["data"]["teams"].values()
    assert sum(t["p_auto_advance"] for t in teams) == pytest.approx(2.0, abs=0.01)
    assert any(t["p_best_third_advance"] > 0 for t in result["data"]["teams"].values())
    for row in result["data"]["teams"].values():
        assert row["p_advance"] == pytest.approx(
            row["p_auto_advance"] + row["p_best_third_advance"], abs=0.0001
        )
    assert "tiebreak_fallbacks" in result["meta"]
    assert "tiebreak_policy" in result["meta"]


async def test_simulate_group_unknown_group_not_found():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_simulate_group(group="Z")
    assert result["error"]["code"] == "NOT_FOUND"


async def test_simulate_group_rejects_blank_or_multichar_group_before_chain():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock()
        for group in ("  ", "AA"):
            result = await intel_tools.football_simulate_group(group=group)
            assert result["error"]["code"] == "INVALID_INPUT"
        mock.fetch.assert_not_awaited()


async def test_simulation_seed_bounds_reject_before_chain():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock()
        for seed in (-1, 2**64):
            bracket = await intel_tools.football_simulate_bracket(seed=seed)
            path = await intel_tools.football_knockout_path(team="ARG", seed=seed)
            assert bracket["error"]["code"] == "INVALID_INPUT"
            assert path["error"]["code"] == "INVALID_INPUT"
        mock.fetch.assert_not_awaited()


async def test_simulate_bracket_flagship_invariants():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as gmock, \
         patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock:
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        result = await intel_tools.football_simulate_bracket(iterations=1500, seed=1)
    data = result["data"]
    assert data["iterations"] == 1500
    assert abs(sum(t["reach_r32"] for t in data["teams"].values()) - 32.0) < 0.01
    assert data["champion"] in data["teams"]
    assert result["meta"]["estimated"] is True
    assert result["meta"]["tiebreak_fallbacks"] == data["tiebreak_fallbacks"]
    assert "model rating" in result["meta"]["tiebreak_policy"]


async def test_knockout_path_returns_team_row():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as gmock, \
         patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock:
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        result = await intel_tools.football_knockout_path(team="FRA", iterations=1200, seed=1)
    assert result["data"]["team"] == "FRA"
    assert 0.0 <= result["data"]["win"] <= 1.0


def _fin(home, away, hs, as_, group, date="2026-06-12"):
    return {
        "home": home,
        "away": away,
        "home_goals": hs,
        "away_goals": as_,
        "group": group,
        "status": "FINISHED",
        "date": date,
    }


def _arg_group_played_out() -> tuple[str, list[dict]]:
    """Argentina's group from the shipped seed, fully played, ARG losing all three.

    Derived from wc2026.json (not hardcoded) so regenerating the draw data from
    live sources cannot silently break these tests.
    """
    wc = load_wc2026()
    letter = next(g for g, codes in wc["groups"].items() if "ARG" in codes)
    arg = wc["teams"]["ARG"]["name"]
    others = [wc["teams"][c]["name"] for c in wc["groups"][letter] if c != "ARG"]
    fixtures = [_fin(arg, name, 0, 1, letter) for name in others]
    fixtures += [
        _fin(a, b, 1, 1, letter)
        for i, a in enumerate(others)
        for b in others[i + 1 :]
    ]
    return letter, fixtures


_ARG_GROUP_LETTER, _GROUP_A_ARG_OUT = _arg_group_played_out()


async def test_simulate_bracket_conditioned_zeros_eliminated_team():
    """Real group results lock in: an eliminated team has win prob 0 + meta count."""
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as gmock, \
         patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock:
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": _GROUP_A_ARG_OUT}))
        result = await intel_tools.football_simulate_bracket(iterations=1000, seed=1)
    assert result["meta"]["conditioned_matches"] == 6
    assert result["data"]["teams"]["ARG"]["win"] == 0.0
    assert result["data"]["teams"]["ARG"]["reach_r32"] == 0.0


async def test_simulate_bracket_degrades_when_fixtures_unavailable():
    """No fixture source -> from-scratch sim with a note, not an error."""
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as gmock, \
         patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock:
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await intel_tools.football_simulate_bracket(iterations=800, seed=1)
    assert "error" not in result
    assert result["meta"]["conditioned_matches"] == 0
    assert "note" in result["meta"]


async def test_simulate_bracket_degrades_when_results_unparseable():
    """A malformed finished fixture (non-numeric goals) -> from-scratch, not an error."""
    from sportiq.football import intel_tools

    bad = _fin("Argentina", "Colombia", "x", 1, "A")  # non-numeric goals -> int() raises
    with patch("sportiq.football.intel_tools.football_groups_chain") as gmock, \
         patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock:
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": [bad]}))
        result = await intel_tools.football_simulate_bracket(iterations=800, seed=1)
    assert "error" not in result
    assert result["meta"]["conditioned_matches"] == 0
    assert "note" in result["meta"]


async def test_simulate_group_meta_counts_conditioned_matches():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as gmock, \
         patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock:
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": _GROUP_A_ARG_OUT}))
        result = await intel_tools.football_simulate_group(
            group=_ARG_GROUP_LETTER, iterations=800
        )
    assert result["meta"]["conditioned_matches"] == 6
    assert result["data"]["teams"]["ARG"]["p_advance"] == 0.0


def _odds_event(home_name, away_name, *, home, draw, away, book="TestBook"):
    return {
        "event_id": "evt1",
        "home": home_name,
        "away": away_name,
        "commence_time": "2026-06-12T00:00:00Z",
        "bookmakers": [{"name": book, "home": home, "draw": draw, "away": away}],
    }


async def test_find_value_bets_surfaces_positive_edge():
    from sportiq.football import intel_tools

    # Generous home price (10.0 -> implied 0.1) vs a favoured home side -> value.
    event = _odds_event("Argentina", "Brazil", home=10.0, draw=4.0, away=1.4)
    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
    ):
        mock_odds.fetch = AsyncMock(return_value=_fr({"events": [event]}, source="theodds"))
        mock_groups.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_find_value_bets(min_edge=0.05)

    data = result["data"]
    assert data["events_analysed"] == 1
    assert any(p["outcome"] == "home" for p in data["value_bets"])
    home = next(p for p in data["value_bets"] if p["outcome"] == "home")
    assert home["edge"] >= 0.05
    assert home["market_odds"] == 10.0
    assert home["bookmaker"] == "TestBook"
    assert result["meta"]["estimated"] is True


async def test_find_value_bets_empty_when_edge_below_threshold():
    from sportiq.football import intel_tools

    # An unreachable edge threshold -> the aggregation surfaces no picks.
    event = _odds_event("Argentina", "Brazil", home=10.0, draw=4.0, away=1.4)
    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
    ):
        mock_odds.fetch = AsyncMock(return_value=_fr({"events": [event]}, source="theodds"))
        mock_groups.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_find_value_bets(min_edge=0.99)
    assert result["data"]["value_bets"] == []
    assert result["data"]["events_analysed"] == 1


async def test_find_value_bets_propagates_odds_staleness():
    from sportiq.football import intel_tools

    event = _odds_event("Argentina", "Brazil", home=10.0, draw=4.0, away=1.4)
    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
    ):
        mock_odds.fetch = AsyncMock(
            return_value=_fr({"events": [event]}, source="cache:stale", is_stale=True)
        )
        mock_groups.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_find_value_bets(min_edge=0.05)
    assert result["meta"]["is_stale"] is True


async def test_find_value_bets_applies_live_elo_when_enabled(monkeypatch):
    from sportiq.football import intel_tools

    # With the opt-in flag on, value bets must nudge the seed from live results
    # (same path as football_match_predictor) and flag it in meta.
    monkeypatch.setattr(intel_tools.settings, "football_live_elo", True)
    event = _odds_event("Argentina", "Brazil", home=10.0, draw=4.0, away=1.4)
    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as mock_fx,
    ):
        mock_odds.fetch = AsyncMock(return_value=_fr({"events": [event]}, source="theodds"))
        mock_groups.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        mock_fx.fetch = AsyncMock(return_value=_fr({"fixtures": _GROUP_A_ARG_OUT}))
        result = await intel_tools.football_find_value_bets(min_edge=0.05)
    assert result["meta"]["live_elo"] is True
    assert result["data"]["events_analysed"] == 1


async def test_find_value_bets_no_live_elo_key_when_disabled():
    from sportiq.football import intel_tools

    # Flag off (test default): no fixtures fetch, no live_elo meta key.
    event = _odds_event("Argentina", "Brazil", home=10.0, draw=4.0, away=1.4)
    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
    ):
        mock_odds.fetch = AsyncMock(return_value=_fr({"events": [event]}, source="theodds"))
        mock_groups.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_find_value_bets(min_edge=0.05)
    assert "live_elo" not in result["meta"]


async def test_find_value_bets_invalid_min_edge():
    from sportiq.football import intel_tools

    result = await intel_tools.football_find_value_bets(min_edge=1.5)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_football_get_squad_unknown_team_returns_envelope(monkeypatch):
    """Unknown team must NOT raise: with no key the api_football adapter is
    skipped and the static_seed terminator serves an empty-but-valid squad.
    Locks the NOT_FOUND terminator invariant against future regressions."""
    from sportiq.config import settings
    from sportiq.football import tools

    monkeypatch.setattr(settings, "apifootball_key", None)

    response = await tools.football_get_squad("Nowhereland")
    assert "error" not in response
    assert response["meta"]["source"] == "static_seed"


# -- football_get_top_scorers -------------------------------------------------


async def test_get_top_scorers_returns_envelope():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_scorers_chain") as mock:
        mock.fetch = AsyncMock(
            return_value=_fr({"scorers": [{"name": "Lionel Messi", "team": "ARG", "goals": 3, "assists": 1}]})
        )
        result = await tools.football_get_top_scorers()
    assert "data" in result
    assert result["data"]["scorers"][0]["name"] == "Lionel Messi"


async def test_get_top_scorers_all_sources_failed():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_scorers_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.football_get_top_scorers()
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- football_get_fixtures -----------------------------------------------------


async def test_get_fixtures_returns_envelope():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_fixtures_chain") as mock:
        mock.fetch = AsyncMock(
            return_value=_fr({"fixtures": [{"home": "ARG", "away": "CAN", "status": "scheduled"}]})
        )
        result = await tools.football_get_fixtures()
    assert "data" in result and "meta" in result


# -- football_get_standings ---------------------------------------------------


async def test_get_standings_all_sources_failed():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_standings_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.football_get_standings()
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- football_get_groups ------------------------------------------------------


async def test_get_groups_all_sources_failed():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.football_get_groups()
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- football_get_match_stats -------------------------------------------------


async def test_get_match_stats_returns_envelope():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_team_stats_chain") as mock:
        mock.fetch = AsyncMock(
            return_value=_fr({"team_stats": {"team": "ARG", "played": 3, "wins": 2, "goals_for": 5, "goals_against": 2}})
        )
        result = await tools.football_get_match_stats(team=26)
    assert "data" in result


# -- envelope meta fields -----------------------------------------------------


async def test_football_meta_has_required_fields():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload(), source="static_seed"))
        result = await tools.football_get_groups()
    for field in ["source", "is_stale", "data_age_seconds", "fallback_used", "duration_ms"]:
        assert field in result["meta"]
