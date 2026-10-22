"""Unit tests for results_state — pure name-join + result partitioning, no I/O."""

from __future__ import annotations

import pytest

from sportiq.football.models.results_state import (
    build_code_index,
    build_results_state,
    derived_standings,
    flip_knockout_winner,
    resolve_code,
    truncate_results_state,
)

# A two-group toy draw is enough to exercise the partitioning logic.
_GROUPS = {"A": ["ARG", "COL", "ECU", "CIV"], "B": ["FRA", "MAR", "CAN", "PER"]}
_TEAMS = {
    "ARG": {"name": "Argentina", "fifa_code": "ARG"},
    "COL": {"name": "Colombia", "fifa_code": "COL"},
    "ECU": {"name": "Ecuador", "fifa_code": "ECU"},
    "CIV": {"name": "Côte d'Ivoire", "fifa_code": "CIV"},
    "FRA": {"name": "France", "fifa_code": "FRA"},
    "MAR": {"name": "Morocco", "fifa_code": "MAR"},
    "CAN": {"name": "Canada", "fifa_code": "CAN"},
    "PER": {"name": "Peru", "fifa_code": "PER"},
}


def _fx(
    home,
    away,
    hs,
    as_,
    date="2026-06-12",
    status="FINISHED",
    **extra,
):
    return {
        "home": home,
        "away": away,
        "home_goals": hs,
        "away_goals": as_,
        "date": date,
        "status": status,
        **extra,
    }


# -- name join -----------------------------------------------------------------


def test_resolve_code_matches_name_accent_and_alias():
    """Names, accents, fifa codes and aliases all resolve to the right code."""
    index = build_code_index(_TEAMS)
    assert resolve_code("Argentina", index) == "ARG"
    assert resolve_code("CÔTE D'IVOIRE", index) == "CIV"  # accents + case
    assert resolve_code("Ivory Coast", index) == "CIV"  # alias
    assert resolve_code("ARG", index) == "ARG"  # raw code
    assert resolve_code("South Korea", index) == "KOR"  # alias (not in draw)


def test_results_state_resolves_cape_verde_and_dr_congo_aliases():
    """openfootball's "Cape Verde" / "DR Congo" resolve against the real WC 2026 draw."""
    import json
    from pathlib import Path

    import sportiq.football as football_pkg

    draw = json.loads((Path(football_pkg.__file__).parent / "data" / "wc2026.json").read_text())
    index = build_code_index(draw["teams"])
    assert resolve_code("Cape Verde", index) == "CPV"
    assert resolve_code("DR Congo", index) == "COD"
    assert resolve_code("DR. Congo", index) == "COD"


def test_unmatched_name_returns_none():
    index = build_code_index(_TEAMS)
    assert resolve_code("Atlantis", index) is None


# -- partitioning --------------------------------------------------------------


def test_completed_and_remaining_partition_half_played_group():
    """A group with 1 played match has it completed and the other 5 remaining."""
    fixtures = [_fx("Argentina", "Colombia", 2, 0)]
    state = build_results_state(fixtures, _GROUPS, _TEAMS)
    g = state.groups["A"]
    assert len(g.completed) == 1
    assert g.completed[0] == ("ARG", "COL", 2, 0)
    assert len(g.remaining) == 5
    assert frozenset(("ARG", "COL")) not in {frozenset(p) for p in g.remaining}
    assert state.matched == 1
    assert state.dropped == 0


def test_unmatched_fixture_dropped_not_crashed():
    """A finished fixture with an unknown team is counted as dropped, never raises."""
    fixtures = [_fx("Argentina", "Atlantis", 1, 0), _fx("France", "Morocco", 1, 1)]
    state = build_results_state(fixtures, _GROUPS, _TEAMS)
    assert state.dropped == 1
    assert state.matched == 1  # only the France-Morocco match resolved


def test_api_football_ft_status_counts_as_finished():
    """api-football reports finished as 'FT'/'AET'/'PEN', not 'FINISHED'."""
    fixtures = [
        _fx("Argentina", "Colombia", 2, 0, status="FT"),
        _fx("Ecuador", "Côte d'Ivoire", 1, 0, status="AET"),
    ]
    state = build_results_state(fixtures, _GROUPS, _TEAMS)
    assert state.matched == 2
    assert ("ARG", "COL", 2, 0) in state.groups["A"].completed


def test_in_play_score_not_locked():
    """A live match carries a current score but must not be treated as final."""
    fixtures = [_fx("Argentina", "Colombia", 1, 0, status="IN_PLAY")]
    state = build_results_state(fixtures, _GROUPS, _TEAMS)
    assert state.matched == 0
    assert len(state.groups["A"].completed) == 0


def test_scheduled_fixture_ignored():
    """Fixtures without final scores are not treated as completed."""
    fixtures = [_fx("Argentina", "Colombia", None, None, status="SCHEDULED")]
    state = build_results_state(fixtures, _GROUPS, _TEAMS)
    assert state.matched == 0
    assert len(state.groups["A"].completed) == 0
    assert len(state.groups["A"].remaining) == 6


def test_cross_group_decisive_result_is_knockout():
    """A finished match between teams from different groups locks a knockout winner."""
    fixtures = [_fx("Argentina", "France", 1, 0)]
    state = build_results_state(fixtures, _GROUPS, _TEAMS)
    assert state.knockout == [("ARG", "FRA", "ARG")]
    # not filed under any group
    assert all(len(g.completed) == 0 for g in state.groups.values())


def test_knockout_draw_on_scoreline_dropped():
    """A cross-group draw can't lock a winner (penalties unknown) -> dropped."""
    fixtures = [_fx("Argentina", "France", 1, 1)]
    state = build_results_state(fixtures, _GROUPS, _TEAMS)
    assert state.knockout == []
    assert state.dropped == 1


def test_same_pair_group_then_knockout_are_both_preserved():
    fixtures = [
        _fx(
            "Argentina",
            "Colombia",
            0,
            1,
            date="2026-06-12",
            match_id=101,
            stage="GROUP_STAGE",
        ),
        _fx(
            "Argentina",
            "Colombia",
            2,
            1,
            date="2026-07-05",
            match_id=202,
            stage="QUARTER_FINALS",
        ),
    ]

    state = build_results_state(fixtures, _GROUPS, _TEAMS)

    assert state.groups["A"].completed == [("ARG", "COL", 0, 1)]
    assert state.knockout == [("ARG", "COL", "ARG")]
    assert state.completed_chrono == [
        ("ARG", "COL", 0, 1),
        ("ARG", "COL", 2, 1),
    ]
    assert state.matched == 2
    assert state.dropped == 0


def test_level_penalty_result_with_explicit_winner_locks_knockout():
    fixtures = [
        _fx(
            "Argentina",
            "France",
            1,
            1,
            status="PEN",
            stage="FINAL",
            winner="France",
        )
    ]

    state = build_results_state(fixtures, _GROUPS, _TEAMS)

    assert state.knockout == [("ARG", "FRA", "FRA")]
    assert state.matched == 1
    assert state.dropped == 0


def test_level_penalty_result_without_winner_is_dropped():
    fixtures = [
        _fx(
            "Argentina",
            "France",
            1,
            1,
            status="PEN",
            stage="FINAL",
        )
    ]

    state = build_results_state(fixtures, _GROUPS, _TEAMS)

    assert state.knockout == []
    assert state.matched == 0
    assert state.dropped == 1


def test_completed_chrono_sorted_by_date():
    fixtures = [
        _fx("Ecuador", "Colombia", 0, 0, date="2026-06-15"),
        _fx("Argentina", "Colombia", 2, 0, date="2026-06-11"),
    ]
    state = build_results_state(fixtures, _GROUPS, _TEAMS)
    dates_order = [m[:2] for m in state.completed_chrono]
    assert dates_order == [("ARG", "COL"), ("ECU", "COL")]


# -- derived standings ---------------------------------------------------------


def test_derived_standings_points_and_order():
    """Standings reflect 3/1/0 points and order by points within a group."""
    fixtures = [
        _fx("Argentina", "Colombia", 2, 0),  # ARG +3
        _fx("Ecuador", "Côte d'Ivoire", 1, 1),  # ECU/CIV +1 each
    ]
    out = derived_standings(fixtures, _GROUPS, _TEAMS)
    group_a = [r for r in out["standings"] if r["group"] == "A"]
    assert group_a[0]["team"] == "Argentina"
    assert group_a[0]["points"] == 3
    assert group_a[0]["played"] == 1
    assert sorted(r["points"] for r in group_a) == [0, 1, 1, 3]
    assert out["source"] == "derived_standings"


# -- what-if helpers (opus cook11 T11.2) ----------------------------------------


def _staged_state():
    """Two group games, one QF (ARG beat FRA) and the final (ARG beat COL)."""
    fixtures = [
        _fx("Argentina", "Colombia", 2, 0, date="2026-06-12", stage="Matchday 1"),
        _fx("France", "Morocco", 1, 1, date="2026-06-13", stage="Matchday 1"),
        _fx("Argentina", "France", 1, 0, date="2026-07-10", stage="Quarter-final"),
        _fx("Argentina", "Colombia", 0, 0, date="2026-07-19", stage="Final", winner="Argentina"),
    ]
    return build_results_state(fixtures, _GROUPS, _TEAMS)


def test_results_state_labels_knockout_rounds_from_stage():
    state = _staged_state()
    assert state.knockout_rounds == {
        frozenset(("ARG", "FRA")): "qf",
        frozenset(("ARG", "COL")): "final",
    }
    assert state.champion == "ARG"


def test_truncate_results_state_from_group_keeps_nothing():
    state = _staged_state()
    out = truncate_results_state(state, "group")
    assert out.knockout == [] and out.completed_chrono == [] and out.matched == 0
    assert all(not g.completed for g in out.groups.values())
    assert all(len(g.remaining) == 6 for g in out.groups.values())
    assert out.champion is None
    assert state.matched == 4  # the input is not mutated


def test_truncate_results_state_from_final_keeps_earlier_knockout_only():
    out = truncate_results_state(_staged_state(), "final")
    assert out.knockout == [("ARG", "FRA", "ARG")]
    assert out.champion is None
    # The group ARG-COL game stays in the Elo walk; the final ARG-COL is dropped.
    assert out.completed_chrono == [
        ("ARG", "COL", 2, 0),
        ("FRA", "MAR", 1, 1),
        ("ARG", "FRA", 1, 0),
    ]
    assert out.matched == 3


def test_truncate_results_state_rejects_unknown_stage():
    with pytest.raises(ValueError):
        truncate_results_state(_staged_state(), "playoffs")


def test_flip_knockout_winner_returns_new_state_with_other_winner():
    state = truncate_results_state(_staged_state(), "final")
    flipped = flip_knockout_winner(state, "FRA", "ARG")
    assert flipped.knockout == [("ARG", "FRA", "FRA")]
    assert state.knockout == [("ARG", "FRA", "ARG")]


def test_flip_knockout_winner_rejects_tie_not_in_state():
    state = truncate_results_state(_staged_state(), "qf")
    with pytest.raises(ValueError):
        flip_knockout_winner(state, "ARG", "FRA")


def test_results_complete_before_false_for_empty_state_and_true_for_group():
    from sportiq.football.models.results_state import (
        GroupResults,
        ResultsState,
        results_complete_before,
    )

    empty = ResultsState(groups={"A": GroupResults(completed=[], remaining=[("MEX", "RSA")])})
    assert results_complete_before(empty, "group") is True
    assert results_complete_before(empty, "r32") is False
    assert results_complete_before(empty, "final") is False
