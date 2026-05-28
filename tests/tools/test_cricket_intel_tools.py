"""Cricket INTEL tool tests — chains stubbed, envelope shape asserted."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sportiq.core.errors import AllSourcesFailedError
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
        + [{"name": f"A_Bowl{i}", "role": "BOWL", "credits": 8.0, "team": "Team A"} for i in range(5)]
    )
    team_b_players = (
        [{"name": f"B_Bat{i}", "role": "BAT", "credits": 9.0, "team": "Team B"} for i in range(5)]
        + [{"name": f"B_All{i}", "role": "ALL", "credits": 8.5, "team": "Team B"} for i in range(3)]
        + [{"name": "B_WK", "role": "WK-BAT", "credits": 9.0, "team": "Team B"}]
        + [{"name": f"B_Bowl{i}", "role": "BOWL", "credits": 8.0, "team": "Team B"} for i in range(5)]
    )
    return (
        _fr({"players": team_a_players, "team": "Team A", "source": "static_seed"}),
        _fr({"players": team_b_players, "team": "Team B", "source": "static_seed"}),
    )


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
            team_a="Team A", team_b="Team B", venue="wankhede"
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


async def test_build_dream11_team_chain_failure_returns_error_envelope():
    from sportiq.cricket import intel_tools

    with patch("sportiq.cricket.intel_tools.pitch_data_chain") as mock_pitch:
        mock_pitch.fetch = AsyncMock(
            side_effect=AllSourcesFailedError("venue down", attempts=[{"name": "static_seed", "error": "missing"}])
        )
        r = await intel_tools.cricket_build_dream11_team(team_a="A", team_b="B", venue="x")

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
            team_a="Team A", team_b="Team B", venue="wankhede"
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
            team_a="Team A", team_b="Team B", venue="wankhede", ownership_threshold=80
        )

    assert r["meta"]["estimated"] is True
    assert "picks" in r["data"]
    assert r["data"]["ownership_threshold"] == 80


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
