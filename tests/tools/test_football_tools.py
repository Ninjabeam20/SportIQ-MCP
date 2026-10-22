"""Football tool tests — chains stubbed, envelope shape + error codes asserted."""

from __future__ import annotations

import asyncio
import time
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
    assert result["data"]["squad"] == []
    assert "note" not in result["data"]
    assert "APIFOOTBALL_KEY" in result["meta"]["note"]


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
        mock.fetch = AsyncMock(
            return_value=_fr({"standings": []}, source="cache:stale", is_stale=True)
        )
        result = await tools.football_get_standings()
    assert result["meta"]["is_stale"] is True


async def test_get_standings_meta_is_stale_when_derived_from_stale_fixtures():
    from sportiq.football import tools

    with patch("sportiq.football.tools.football_standings_chain") as mock:
        mock.fetch = AsyncMock(
            return_value=_fr(
                {"standings": [], "upstream_is_stale": True}, source="derived_standings"
            )
        )
        result = await tools.football_get_standings()
    assert result["meta"]["is_stale"] is True
    assert "upstream_is_stale" not in result["data"]


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


async def test_xg_model_accepts_full_team_names():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        by_name = await intel_tools.football_xg_model(home_team="Spain", away_team="Argentina")
        by_code = await intel_tools.football_xg_model(home_team="ESP", away_team="ARG")
    assert by_name["data"] == by_code["data"]
    assert by_name["data"]["home_team"] == "ESP"


async def test_simulate_group_models_contextual_best_third_advancement():
    from sportiq.football import intel_tools

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        result = await intel_tools.football_simulate_group(group="A", iterations=1500)
    teams = result["data"]["teams"].values()
    assert sum(t["p_auto_advance"] for t in teams) == pytest.approx(2.0, abs=0.01)
    assert any(t["p_best_third_advance"] > 0 for t in result["data"]["teams"].values())
    for row in result["data"]["teams"].values():
        assert row["p_advance"] == pytest.approx(
            row["p_auto_advance"] + row["p_best_third_advance"], abs=0.00011
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


async def test_simulate_group_accepts_group_prefix():
    from sportiq.football import intel_tools

    groups = []
    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        for group in ("Group A", "group a", "A"):
            result = await intel_tools.football_simulate_group(group=group, iterations=100)
            groups.append(result["data"]["group"])
    assert groups == ["A", "A", "A"]


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

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
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

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
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
    fixtures += [_fin(a, b, 1, 1, letter) for i, a in enumerate(others) for b in others[i + 1 :]]
    return letter, fixtures


_ARG_GROUP_LETTER, _GROUP_A_ARG_OUT = _arg_group_played_out()


async def test_simulate_bracket_conditioned_zeros_eliminated_team():
    """Real group results lock in: an eliminated team has win prob 0 + meta count."""
    from sportiq.football import intel_tools

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": _GROUP_A_ARG_OUT}))
        result = await intel_tools.football_simulate_bracket(iterations=1000, seed=1)
    assert result["meta"]["conditioned_matches"] == 6
    assert result["data"]["teams"]["ARG"]["win"] == 0.0
    assert result["data"]["teams"]["ARG"]["reach_r32"] == 0.0


async def test_simulate_bracket_degrades_when_fixtures_unavailable():
    """No fixture source -> from-scratch sim with a note, not an error."""
    from sportiq.football import intel_tools

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
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
    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": [bad]}))
        result = await intel_tools.football_simulate_bracket(iterations=800, seed=1)
    assert "error" not in result
    assert result["meta"]["conditioned_matches"] == 0
    assert "note" in result["meta"]


async def test_simulate_group_meta_counts_conditioned_matches():
    from sportiq.football import intel_tools

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": _GROUP_A_ARG_OUT}))
        result = await intel_tools.football_simulate_group(group=_ARG_GROUP_LETTER, iterations=800)
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


async def test_find_value_bets_maps_alias_names():
    from sportiq.football import intel_tools

    # The seed names KOR "South Korea"; providers send "Korea Republic".
    event = _odds_event("Korea Republic", "Mexico", home=3.0, draw=3.2, away=2.4)
    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
    ):
        mock_odds.fetch = AsyncMock(return_value=_fr({"events": [event]}, source="theodds"))
        mock_groups.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_find_value_bets(team="KOR", min_edge=0.99)
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


async def test_xg_model_meta_is_stale_when_live_elo_fixtures_stale(monkeypatch):
    from sportiq.football import intel_tools

    # Live Elo reads the fixtures chain; its staleness must reach meta.
    monkeypatch.setattr(intel_tools.settings, "football_live_elo", True)
    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as mock_fx,
    ):
        mock_groups.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        mock_fx.fetch = AsyncMock(
            return_value=_fr({"fixtures": _GROUP_A_ARG_OUT}, source="cache:stale", is_stale=True)
        )
        result = await intel_tools.football_xg_model(home_team="ARG", away_team="BRA")
    assert result["meta"]["is_stale"] is True


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


async def test_find_value_bets_staleness_from_groups():
    from sportiq.football import intel_tools

    event = _odds_event("Argentina", "Brazil", home=10.0, draw=4.0, away=1.4)
    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
    ):
        mock_odds.fetch = AsyncMock(
            return_value=_fr({"events": [event]}, source="theodds", is_stale=False)
        )
        mock_groups.fetch = AsyncMock(return_value=_fr(_draw_payload(), is_stale=True))
        result = await intel_tools.football_find_value_bets(min_edge=0.05)
    assert result["meta"]["is_stale"] is True


async def test_find_value_bets_invalid_min_edge():
    from sportiq.football import intel_tools

    result = await intel_tools.football_find_value_bets(min_edge=1.5)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_find_value_bets_odds_unexpected_error_reraises():
    from sportiq.football import intel_tools

    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
    ):
        mock_odds.fetch = AsyncMock(side_effect=RuntimeError("unexpected odds failure"))
        mock_groups.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        with pytest.raises(RuntimeError, match="unexpected odds failure"):
            await intel_tools.football_find_value_bets(min_edge=0.05)


async def test_find_value_bets_groups_unexpected_error_reraises():
    from sportiq.football import intel_tools

    event = _odds_event("Argentina", "Brazil", home=10.0, draw=4.0, away=1.4)
    with (
        patch("sportiq.football.intel_tools.football_odds_chain") as mock_odds,
        patch("sportiq.football.intel_tools.football_groups_chain") as mock_groups,
    ):
        mock_odds.fetch = AsyncMock(return_value=_fr({"events": [event]}, source="theodds"))
        mock_groups.fetch = AsyncMock(side_effect=RuntimeError("unexpected groups failure"))
        with pytest.raises(RuntimeError, match="unexpected groups failure"):
            await intel_tools.football_find_value_bets(min_edge=0.05)


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
            return_value=_fr(
                {"scorers": [{"name": "Lionel Messi", "team": "ARG", "goals": 3, "assists": 1}]}
            )
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
            return_value=_fr(
                {
                    "team_stats": {
                        "team": "ARG",
                        "played": 3,
                        "wins": 2,
                        "goals_for": 5,
                        "goals_against": 2,
                    }
                }
            )
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


# -- 1e sim-model errors -> INVALID_INPUT ---------------------------------------


def _malformed_draw_payload() -> dict:
    # 1 group of 3 teams: simulate_group_stage expects 12 groups of 4.
    return {
        "groups": {"A": ["X", "Y", "Z"]},
        "format": {},
        "teams": {},
        "ratings": {"X": 1500.0, "Y": 1500.0, "Z": 1500.0},
        "source": "static_seed",
    }


async def test_simulate_group_malformed_draw_returns_invalid_input():
    from sportiq.football import intel_tools

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_malformed_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        result = await intel_tools.football_simulate_group(group="A", iterations=100)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_simulate_bracket_malformed_draw_returns_invalid_input():
    from sportiq.football import intel_tools

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_malformed_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        result = await intel_tools.football_simulate_bracket(iterations=100, seed=1)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_knockout_path_malformed_draw_returns_invalid_input():
    from sportiq.football import intel_tools

    # "X" is in the (malformed) draw, so it passes the draw-based participation
    # check (opus cook6 T6.4) and reaches the simulator, which rejects the draw.
    payload = _malformed_draw_payload()
    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(payload))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        result = await intel_tools.football_knockout_path(team="X", iterations=100, seed=1)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_simulate_bracket_unseen_third_combo_returns_invalid_input():
    from sportiq.football import intel_tools

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
        patch("sportiq.football.intel_tools.simulate_tournament", side_effect=KeyError("ZZZZZZZZ")),
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        result = await intel_tools.football_simulate_bracket(iterations=100, seed=1)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_simulate_bracket_does_not_block_event_loop():
    """The Monte Carlo runs in a worker thread, so the event loop keeps ticking."""
    from sportiq.football import intel_tools

    def _slow_sim(*args, **kwargs):
        time.sleep(0.3)
        return {"teams": {}, "champion": None, "iterations": 100, "tiebreak_fallbacks": 0}

    ticks = 0

    async def _ticker():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
        patch("sportiq.football.intel_tools.simulate_tournament", _slow_sim),
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        ticker = asyncio.create_task(_ticker())
        try:
            result = await intel_tools.football_simulate_bracket(iterations=100, seed=1)
        finally:
            ticker.cancel()
    assert "data" in result
    assert ticks >= 10


# -- cook6: participation, default ratings, simulation mode --------------------


async def _complete_wc2026_fixtures() -> list[dict]:
    """The downloaded 2026-10-22 openfootball snapshot, parsed by the real adapter."""
    import json
    from pathlib import Path

    import respx
    from httpx import Response

    from sportiq.football.adapters.openfootball import (
        _OPENFOOTBALL_URL,
        OpenFootballFixturesAdapter,
    )

    path = (
        Path(__file__).parent.parent / "fixtures" / "openfootball" / "worldcup-2026-complete.json"
    )
    with respx.mock:
        respx.get(_OPENFOOTBALL_URL).mock(
            return_value=Response(200, json=json.loads(path.read_text()))
        )
        result = await OpenFootballFixturesAdapter().fetch()
    return result["fixtures"]


async def test_knockout_path_rejects_non_entrant_ita():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as gmock:
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_knockout_path(team="ITA", iterations=100, seed=1)
    assert result["error"]["code"] == "NOT_FOUND"
    assert "not a World Cup 2026 entrant" in result["error"]["message"]


async def test_xg_model_accepts_ksa():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_xg_model(home_team="KSA", away_team="ESP")
    assert "error" not in result
    assert result["data"]["home_team"] == "KSA"
    assert "default_rating_teams" not in result["meta"]  # SAU seed value via the alias


async def test_xg_model_uses_default_rating_and_discloses_it():
    from sportiq.football import intel_tools

    with patch("sportiq.football.intel_tools.football_groups_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        result = await intel_tools.football_xg_model(home_team="SWE", away_team="ESP")
    assert "error" not in result
    assert result["meta"]["default_rating_teams"] == ["SWE"]
    assert "default" in result["meta"]["note"]


async def test_simulate_bracket_meta_lists_default_rating_teams():
    from sportiq.football import intel_tools

    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        result = await intel_tools.football_simulate_bracket(iterations=100, seed=1)
    assert result["meta"]["default_rating_teams"] == [
        "BIH", "COD", "CPV", "CUW", "CZE", "HAI", "IRQ", "JOR", "RSA", "SWE", "TUR",
    ]  # fmt: skip


async def test_simulate_bracket_meta_mode_completed_names_champion():
    from sportiq.football import intel_tools

    fixtures = await _complete_wc2026_fixtures()
    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": fixtures}, source="openfootball"))
        result = await intel_tools.football_simulate_bracket(iterations=200, seed=42)
    assert result["meta"]["mode"] == "completed"
    assert result["meta"]["champion"] == "ESP"
    assert result["data"]["teams"]["ESP"]["win"] == 1.0


async def test_simulate_bracket_meta_mode_prior_when_static_seed():
    from sportiq.football import intel_tools
    from sportiq.football.adapters.static_seed import StaticSeedFixturesAdapter

    seed_fixtures = await StaticSeedFixturesAdapter().fetch()
    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr(seed_fixtures, source="static_seed"))
        result = await intel_tools.football_simulate_bracket(iterations=100, seed=1)
    assert result["meta"]["mode"] == "pre_tournament_prior"
    assert "reconstructed pre-tournament simulation" in result["meta"]["note"]
    assert "champion" not in result["meta"]


# -- football_what_if + completed-mode short-circuit (opus cook11 T11.2/T11.3) --


async def _call_with_complete_results(tool, **kwargs):
    fixtures = await _complete_wc2026_fixtures()
    with (
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": fixtures}, source="openfootball"))
        return await tool(**kwargs)


async def test_what_if_replay_from_final_simulates_only_the_final():
    from sportiq.football import intel_tools

    result = await _call_with_complete_results(
        intel_tools.football_what_if, replay_from="final", iterations=400, seed=3
    )
    teams = result["data"]["teams"]
    assert teams["ESP"]["win"] > 0 and teams["ARG"]["win"] > 0
    assert teams["ESP"]["win"] + teams["ARG"]["win"] == pytest.approx(1.0)
    assert all(row["win"] == 0.0 for code, row in teams.items() if code not in ("ESP", "ARG"))
    assert result["meta"]["mode"] == "what_if"
    assert result["meta"]["replay_from"] == "final"
    assert result["meta"]["flipped"] is None


async def test_what_if_flip_semi_final_puts_france_in_final():
    from sportiq.football import intel_tools

    result = await _call_with_complete_results(
        intel_tools.football_what_if,
        replay_from="final",
        flip_winner_of="ESP-FRA",
        iterations=400,
        seed=3,
    )
    teams = result["data"]["teams"]
    assert teams["FRA"]["win"] + teams["ARG"]["win"] == pytest.approx(1.0)
    assert teams["ESP"]["win"] == 0.0
    assert teams["FRA"]["reach_final"] == 1.0
    assert result["meta"]["flipped"] == {"tie": ["ESP", "FRA"], "winner": "FRA"}


async def test_what_if_replay_from_group_is_full_prior():
    from sportiq.football import intel_tools

    seen = {}

    def fake_sim(groups, ratings, n_iter, seed, results):
        seen["results"] = results
        teams = {code: {"win": 1 / 48} for codes in groups.values() for code in codes}
        return {"teams": teams, "iterations": n_iter, "champion": "ESP", "tiebreak_fallbacks": 0}

    with patch("sportiq.football.intel_tools.simulate_tournament", fake_sim):
        result = await _call_with_complete_results(
            intel_tools.football_what_if, replay_from="group", iterations=100
        )
    state = seen["results"]
    assert state.knockout == [] and state.matched == 0
    assert all(not g.completed for g in state.groups.values())
    assert result["meta"]["flipped"] is None
    assert result["meta"]["conditioned_matches"] == 0
    assert all(row["win"] > 0 for row in result["data"]["teams"].values())


async def test_what_if_rejects_flip_outside_kept_stages():
    from sportiq.football import intel_tools

    # The ESP-FRA semi-final is not kept when replaying from the semi-finals.
    result = await _call_with_complete_results(
        intel_tools.football_what_if, replay_from="sf", flip_winner_of="ESP-FRA"
    )
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_what_if_rejects_unreadable_flip():
    from sportiq.football import intel_tools

    result = await _call_with_complete_results(
        intel_tools.football_what_if, replay_from="final", flip_winner_of="Spain"
    )
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_simulate_bracket_completed_mode_skips_monte_carlo():
    from sportiq.football import intel_tools

    def must_not_run(*args, **kwargs):
        raise AssertionError("simulate_tournament must not run for a completed tournament")

    with patch("sportiq.football.intel_tools.simulate_tournament", must_not_run):
        result = await _call_with_complete_results(
            intel_tools.football_simulate_bracket, iterations=10000
        )
    assert result["meta"]["mode"] == "completed"
    assert result["meta"]["iterations"] == 0
    assert result["data"]["teams"]["ESP"]["win"] == 1.0
    assert result["data"]["champion"] == "ESP"
    assert next(iter(result["data"]["teams"])) == "ESP"


async def test_knockout_path_completed_mode_returns_exact_rounds():
    from sportiq.football import intel_tools

    def must_not_run(*args, **kwargs):
        raise AssertionError("simulate_tournament must not run for a completed tournament")

    with patch("sportiq.football.intel_tools.simulate_tournament", must_not_run):
        result = await _call_with_complete_results(intel_tools.football_knockout_path, team="FRA")
    data = result["data"]
    # France lost the ESP semi-final.
    assert (data["reach_r32"], data["reach_r16"], data["reach_qf"]) == (1.0, 1.0, 1.0)
    assert (data["reach_sf"], data["reach_final"], data["win"]) == (1.0, 0.0, 0.0)
    assert result["meta"]["iterations"] == 0


async def test_seeded_bracket_result_is_memoised():
    from sportiq.football import intel_tools

    calls = []

    def counting_sim(groups, ratings, n_iter, seed, results):
        calls.append(seed)
        teams = {code: {"win": 0.0} for codes in groups.values() for code in codes}
        return {"teams": teams, "iterations": n_iter, "champion": "ESP", "tiebreak_fallbacks": 0}

    with (
        patch("sportiq.football.intel_tools.simulate_tournament", counting_sim),
        patch("sportiq.football.intel_tools.football_groups_chain") as gmock,
        patch("sportiq.football.intel_tools.football_fixtures_chain") as fmock,
    ):
        gmock.fetch = AsyncMock(return_value=_fr(_draw_payload()))
        fmock.fetch = AsyncMock(return_value=_fr({"fixtures": []}))
        first = await intel_tools.football_simulate_bracket(iterations=100, seed=9)
        second = await intel_tools.football_simulate_bracket(iterations=100, seed=9)
        await intel_tools.football_simulate_bracket(iterations=100)  # unseeded: never memoised
        await intel_tools.football_simulate_bracket(iterations=100)
    assert calls == [9, None, None]
    assert first["data"] == second["data"]
