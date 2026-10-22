"""Cricket INTEL tool tests — chains stubbed, envelope shape asserted."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.fallback import FallbackResult


def _fr(value, source="static_seed"):
    return FallbackResult(
        value=value,
        source=source,
        is_stale=False,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )


def _venue_record():
    return {
        "key": "wankhede",
        "name": "Wankhede Stadium",
        "city": "Mumbai",
        "pitch_type": "batting",
        "avg_first_innings": 178,
        "source": "static_seed",
    }


def _two_team_squads():
    """Two teams' worth of normalised squad payloads — enough for a feasible XI."""
    team_a_players = (
        [{"name": f"A_Bat{i}", "role": "BAT", "credits": 9.0, "team": "Team A"} for i in range(5)]
        + [{"name": f"A_All{i}", "role": "ALL", "credits": 8.5, "team": "Team A"} for i in range(3)]
        + [{"name": "A_WK", "role": "WK-BAT", "credits": 9.0, "team": "Team A"}]
        + [
            {"name": f"A_Bowl{i}", "role": "BOWL", "credits": 8.0, "team": "Team A"}
            for i in range(5)
        ]
    )
    team_b_players = (
        [{"name": f"B_Bat{i}", "role": "BAT", "credits": 9.0, "team": "Team B"} for i in range(5)]
        + [{"name": f"B_All{i}", "role": "ALL", "credits": 8.5, "team": "Team B"} for i in range(3)]
        + [{"name": "B_WK", "role": "WK-BAT", "credits": 9.0, "team": "Team B"}]
        + [
            {"name": f"B_Bowl{i}", "role": "BOWL", "credits": 8.0, "team": "Team B"}
            for i in range(5)
        ]
    )
    return (
        _fr({"players": team_a_players, "team": "Team A", "source": "static_seed"}),
        _fr({"players": team_b_players, "team": "Team B", "source": "static_seed"}),
    )


async def test_candidate_pool_fetches_both_squads_concurrently():
    """The two squad fetches are independent — they must overlap, not serialize
    (one upstream round-trip instead of two on a cold cache)."""
    from sportiq.cricket import intel_tools

    squad_a, squad_b = _two_team_squads()
    responses = [squad_a, squad_b]
    in_flight = 0
    max_in_flight = 0

    class _TrackingChain:
        async def fetch(self, **kwargs):
            nonlocal in_flight, max_in_flight
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            response = responses.pop(0)
            await asyncio.sleep(0.01)
            in_flight -= 1
            return response

    with patch("sportiq.cricket.intel_tools.squad_chain", _TrackingChain()):
        candidates, results, _excluded = await intel_tools._candidate_pool(
            "Team A", "Team B", _venue_record()
        )

    assert max_in_flight == 2
    assert len(candidates) == 28
    assert len(results) == 2


# -- cricket_build_dream11_team -----------------------------------------------


async def test_build_dream11_team_returns_xi_envelope():
    from sportiq.cricket import intel_tools

    squad_a, squad_b = _two_team_squads()
    with (
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
    ):
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
        response = await intel_tools.cricket_build_dream11_team(
            team_a="MI", team_b="CSK", venue="wankhede"
        )

    assert "data" in response
    assert len(response["data"]["players"]) == 11
    assert response["data"]["total_credits"] <= 100
    teams = [p["team"] for p in response["data"]["players"]]
    for t in set(teams):
        assert teams.count(t) <= 7
    assert response["data"]["captain"] != response["data"]["vice_captain"]
    assert response["meta"]["estimated"] is True


async def test_build_dream11_team_empty_args_returns_invalid_input():
    from sportiq.cricket import intel_tools

    r = await intel_tools.cricket_build_dream11_team(team_a="", team_b="B", venue="x")
    assert r["error"]["code"] == "INVALID_INPUT"


async def test_build_dream11_team_no_args_returns_invalid_input():
    from sportiq.cricket import intel_tools

    # Neither match_id nor team_a/team_b/venue supplied.
    r = await intel_tools.cricket_build_dream11_team()
    assert r["error"]["code"] == "INVALID_INPUT"


async def test_dream11_without_args_explains_both_forms():
    from sportiq.cricket import intel_tools

    r = await intel_tools.cricket_build_dream11_team()
    assert r["error"]["code"] == "INVALID_INPUT"
    assert "match_id" in r["error"]["message"]
    assert "team_a" in r["error"]["message"]
    assert "team_a='MI', team_b='CSK', venue='wankhede'" in r["error"]["suggestion"]


async def test_captain_without_args_explains_both_forms():
    from sportiq.cricket import intel_tools

    r = await intel_tools.cricket_captain_recommendation()
    assert r["error"]["code"] == "INVALID_INPUT"
    assert "match_id" in r["error"]["message"]
    assert "team_a='MI', team_b='CSK', venue='wankhede'" in r["error"]["suggestion"]


async def test_differential_without_args_explains_both_forms():
    from sportiq.cricket import intel_tools

    r = await intel_tools.cricket_differential_picks()
    assert r["error"]["code"] == "INVALID_INPUT"
    assert "match_id" in r["error"]["message"]
    assert "team_a='MI', team_b='CSK', venue='wankhede'" in r["error"]["suggestion"]


async def test_dream11_unknown_team_returns_not_found_with_valid_codes():
    from sportiq.cricket import intel_tools

    r = await intel_tools.cricket_build_dream11_team(team_a="Foo", team_b="CSK", venue="wankhede")
    assert r["error"]["code"] == "NOT_FOUND"
    assert "MI" in r["error"]["suggestion"]


async def test_dream11_accepts_full_team_names():
    from sportiq.cricket import intel_tools

    async def _run(team_a: str, team_b: str):
        squad_a, squad_b = _two_team_squads()
        with (
            patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
            patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
        ):
            mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
            mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
            response = await intel_tools.cricket_build_dream11_team(
                team_a=team_a, team_b=team_b, venue="wankhede"
            )
            teams_asked = [c.kwargs["team"] for c in mock_squad.fetch.call_args_list]
        return response, teams_asked

    by_name, asked_by_name = await _run("Mumbai Indians", "Chennai Super Kings")
    by_code, asked_by_code = await _run("MI", "CSK")
    assert asked_by_name == asked_by_code == ["MI", "CSK"]
    assert "data" in by_name
    names = sorted(p["name"] for p in by_name["data"]["players"])
    assert names == sorted(p["name"] for p in by_code["data"]["players"])


async def test_build_dream11_team_match_id_resolves_and_builds():
    from sportiq.cricket import intel_tools

    squad_a, squad_b = _two_team_squads()
    with (
        patch("sportiq.cricket.intel_tools.resolve_match") as mock_resolve,
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
    ):
        mock_resolve.return_value = {"team_a": "MI", "team_b": "CSK", "venue": "wankhede"}
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
        response = await intel_tools.cricket_build_dream11_team(match_id="m123")

    mock_resolve.assert_called_once_with("m123")
    assert "data" in response
    assert len(response["data"]["players"]) == 11
    assert response["meta"]["estimated"] is True


async def test_build_dream11_team_chain_failure_returns_error_envelope():
    from sportiq.cricket import intel_tools

    with patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch:
        mock_pitch.fetch = AsyncMock(
            side_effect=AllSourcesFailedError(
                "venue down", attempts=[{"name": "static_seed", "error": "missing"}]
            )
        )
        r = await intel_tools.cricket_build_dream11_team(team_a="MI", team_b="CSK", venue="x")

    assert r["error"]["code"] == "ALL_SOURCES_FAILED"


# -- cricket_captain_recommendation -------------------------------------------


async def test_captain_recommendation_returns_top3():
    from sportiq.cricket import intel_tools

    squad_a, squad_b = _two_team_squads()
    with (
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
    ):
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
        r = await intel_tools.cricket_captain_recommendation(
            team_a="MI", team_b="CSK", venue="wankhede"
        )

    assert len(r["data"]["candidates"]) == 3
    # Sorted descending by projected_points.
    pps = [c["projected_points"] for c in r["data"]["candidates"]]
    assert pps == sorted(pps, reverse=True)
    assert r["meta"]["estimated"] is True


# -- cricket_differential_picks -----------------------------------------------


async def test_differential_picks_flags_estimated_meta():
    from sportiq.cricket import intel_tools

    squad_a, squad_b = _two_team_squads()
    with (
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
    ):
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
        r = await intel_tools.cricket_differential_picks(
            team_a="MI", team_b="CSK", venue="wankhede", ownership_threshold=80
        )

    assert r["meta"]["estimated"] is True
    assert "picks" in r["data"]
    assert r["data"]["ownership_threshold"] == 80


async def test_differential_picks_returns_cheap_players_at_default_threshold():
    # Regression for audit finding #4: the old `credits * 7` proxy put even a
    # 7.0-credit player at 49% ownership, so the default 20% threshold always
    # returned []. The recalibrated curve maps 7.0 credits to ~5% ownership.
    from sportiq.cricket import intel_tools

    cheap = _fr(
        {
            "players": [{"name": "Cheap Punt", "role": "BAT", "credits": 7.0, "team": "Team A"}],
            "team": "Team A",
            "source": "static_seed",
        }
    )
    empty = _fr({"players": [], "team": "Team B", "source": "static_seed"})
    with (
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
    ):
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[cheap, empty])
        r = await intel_tools.cricket_differential_picks(
            team_a="MI", team_b="CSK", venue="wankhede"
        )

    assert len(r["data"]["picks"]) == 1
    assert r["data"]["picks"][0]["name"] == "Cheap Punt"
    assert r["data"]["picks"][0]["estimated_ownership_pct"] <= 20


# -- cricket_player_form_index ------------------------------------------------


async def test_player_form_index_returns_score_and_trend():
    from sportiq.cricket import intel_tools

    cricapi_payload = {
        "data": {
            "stats": [
                {"fn": "batting", "matchtype": "t20i", "stat": "Average", "value": "50.0"},
                {"fn": "batting", "matchtype": "t20i", "stat": "Strike Rate", "value": "140.0"},
            ]
        }
    }
    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_fr(cricapi_payload, source="cricapi"))
        r = await intel_tools.cricket_player_form_index(player_id="p1")

    assert "form_score" in r["data"]
    assert 0.0 <= r["data"]["form_score"] <= 100.0
    assert r["meta"]["source"] == "cricapi"
    assert "data_age_seconds" in r["meta"]
    assert "fallback_used" in r["meta"]


async def test_player_form_index_empty_id_returns_invalid_input():
    from sportiq.cricket import intel_tools

    r = await intel_tools.cricket_player_form_index(player_id="")
    assert r["error"]["code"] == "INVALID_INPUT"


async def test_player_form_index_chain_failure_returns_error_envelope():
    from sportiq.cricket import intel_tools

    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(
            side_effect=AllSourcesFailedError(
                "no stats", attempts=[{"name": "cricapi", "error": "401"}]
            )
        )
        r = await intel_tools.cricket_player_form_index(player_id="p1")

    assert r["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_player_form_index_not_found_returns_envelope():
    from sportiq.cricket import intel_tools

    with patch("sportiq.cricket.intel_tools.player_stats_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=NotFoundError("player missing"))
        r = await intel_tools.cricket_player_form_index(player_id="p1")

    assert r["error"]["code"] == "NOT_FOUND"


# -- cricket_get_pitch_report -------------------------------------------------


async def test_pitch_report_summarises_venue():
    from sportiq.cricket import intel_tools

    with patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(return_value=_fr(_venue_record()))
        r = await intel_tools.cricket_get_pitch_report(venue="wankhede")

    assert r["data"]["pitch_type"] == "batting"
    assert r["data"]["batting_friendly"] > 0.5
    assert "recommendation" in r["data"]


async def test_pitch_report_empty_venue_returns_invalid_input():
    from sportiq.cricket import intel_tools

    r = await intel_tools.cricket_get_pitch_report(venue="")
    assert r["error"]["code"] == "INVALID_INPUT"


async def test_dream11_solve_does_not_block_event_loop():
    """The CBC solve runs in a worker thread, so the event loop keeps ticking."""
    from sportiq.cricket import intel_tools

    def _slow_solve(candidates, strategy="balanced"):
        time.sleep(0.3)
        return {"players": [], "captain": None, "vice_captain": None, "total_credits": 0}

    ticks = 0

    async def _ticker():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    squad_a, squad_b = _two_team_squads()
    with (
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
        patch("sportiq.cricket.intel_tools._solve_dream11", _slow_solve),
    ):
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
        ticker = asyncio.create_task(_ticker())
        try:
            response = await intel_tools.cricket_build_dream11_team(
                team_a="MI", team_b="CSK", venue="wankhede"
            )
        finally:
            ticker.cancel()
    assert "data" in response
    assert ticks >= 10


# -- opus cook8: series_id, honest meta, credits ------------------------------


async def test_dream11_match_id_path_passes_series_id_to_squad_chain():
    from sportiq.cricket import intel_tools

    squad_a, squad_b = _two_team_squads()
    with (
        patch("sportiq.cricket.intel_tools.resolve_match") as mock_resolve,
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
    ):
        mock_resolve.return_value = {
            "team_a": "MI",
            "team_b": "CSK",
            "venue": "wankhede",
            "series_id": "s2026",
        }
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
        await intel_tools.cricket_build_dream11_team(match_id="m123")

    calls = mock_squad.fetch.await_args_list
    assert [c.kwargs["series_id"] for c in calls] == ["s2026", "s2026"]


async def test_dream11_meta_labels_default_form_and_scoring_profile():
    from sportiq.cricket import intel_tools
    from sportiq.cricket.data.scoring import SCORING_PROFILE

    squad_a, squad_b = _two_team_squads()
    with (
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
    ):
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
        r = await intel_tools.cricket_build_dream11_team(
            team_a="MI", team_b="CSK", venue="wankhede"
        )

    assert r["meta"]["form_source"] == "default_neutral"
    assert "role-based projections" in r["meta"]["note"]
    assert r["meta"]["scoring_profile"] == SCORING_PROFILE


async def test_captain_and_differential_meta_label_default_form():
    from sportiq.cricket import intel_tools

    for tool in (
        intel_tools.cricket_captain_recommendation,
        intel_tools.cricket_differential_picks,
    ):
        squad_a, squad_b = _two_team_squads()
        with (
            patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
            patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
        ):
            mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
            mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
            r = await tool(team_a="MI", team_b="CSK", venue="wankhede")
        assert r["meta"]["form_source"] == "default_neutral", tool.__name__
        assert "role-based projections" in r["meta"]["note"]


async def test_differential_picks_label_ownership_as_heuristic():
    from sportiq.cricket import intel_tools

    squad_a, squad_b = _two_team_squads()
    with (
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
    ):
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
        r = await intel_tools.cricket_differential_picks(
            team_a="MI", team_b="CSK", venue="wankhede", ownership_threshold=100
        )

    assert r["data"]["picks"]
    assert all(p["ownership_pct_estimated"] is True for p in r["data"]["picks"])
    assert r["meta"]["ownership_source"] == "heuristic_from_credits"


async def test_dream11_excludes_players_with_missing_credits():
    from sportiq.cricket import intel_tools

    squad_a, squad_b = _two_team_squads()
    squad_a.value["players"].append(
        {"name": "No Price", "role": "BAT", "credits": None, "team": "Team A"}
    )
    with (
        patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch,
        patch("sportiq.cricket.intel_tools.squad_chain") as mock_squad,
    ):
        mock_pitch.fetch = AsyncMock(return_value=_fr(_venue_record()))
        mock_squad.fetch = AsyncMock(side_effect=[squad_a, squad_b])
        r = await intel_tools.cricket_build_dream11_team(
            team_a="MI", team_b="CSK", venue="wankhede"
        )

    assert r["meta"]["excluded_missing_credits"] == 1
    assert "No Price" not in [p["name"] for p in r["data"]["players"]]


# -- opus cook9 T9.1: the generated squad seed makes the old infeasible pairs solvable --


async def test_dream11_csk_lsg_solves_with_generated_seed():
    # No chain mocks: no credentials in tests, so the squad chain falls to the
    # Cricsheet-generated static seed (old seed: 2 BATs, infeasible).
    from sportiq.cricket import intel_tools

    r = await intel_tools.cricket_build_dream11_team(team_a="CSK", team_b="LSG", venue="ekana")
    assert "error" not in r, r.get("error")
    assert len(r["data"]["players"]) == 11


async def test_dream11_pbks_lsg_solves_with_generated_seed():
    from sportiq.cricket import intel_tools

    r = await intel_tools.cricket_build_dream11_team(team_a="PBKS", team_b="LSG", venue="ekana")
    assert "error" not in r, r.get("error")
    assert len(r["data"]["players"]) == 11
