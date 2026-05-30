"""The committed wc2026_bracket.json must encode the official structure faithfully."""
from __future__ import annotations

import json
from math import comb
from pathlib import Path

_BRACKET = json.loads(
    (Path(__file__).resolve().parents[2]
     / "src" / "sportiq" / "football" / "data" / "wc2026_bracket.json").read_text()
)


def test_r32_has_sixteen_matches():
    assert sorted(int(k) for k in _BRACKET["r32"]) == list(range(73, 89))


def test_bracket_order_is_the_sixteen_r32_matches():
    assert sorted(_BRACKET["bracket_order"]) == list(range(73, 89))
    assert len(_BRACKET["bracket_order"]) == 16


def test_allocation_has_495_bijective_rows():
    alloc = _BRACKET["third_allocation"]
    assert len(alloc) == comb(12, 8) == 495
    for combo, row in alloc.items():
        assert set(row.values()) == set(combo)        # bijection onto qualifying set
        assert len(set(row.values())) == 8            # no duplicate third
        for slot, grp in row.items():
            assert slot[1] != grp                     # never face your own group's third


def test_no_r32_match_pairs_same_group_winner_and_runner():
    for m in _BRACKET["r32"].values():
        s1, s2 = m["slot1"], m["slot2"]
        if s1[0] in "12" and s2[0] in "12":
            assert s1[1:] != s2[1:]


def test_build_r32_runtime_32_distinct_teams_no_intra_group_pair():
    """_build_r32 must produce 32 distinct teams with no intra-group R32 match."""
    from sportiq.football.models.bracket_sim import _build_r32

    groups = list("ABCDEFGHIJKL")
    # Give each group a unique winner and runner (no overlap)
    winners = {g: f"W{g}" for g in groups}
    runners = {g: f"R{g}" for g in groups}
    # Pick first 8 groups as best-thirds; sorted letters = "ABCDEFGH" which is
    # guaranteed to exist in third_allocation (it's a valid C(12,8) combo).
    best_third_groups = list("ABCDEFGH")
    best_thirds = {g: f"T{g}" for g in best_third_groups}

    r32 = _build_r32(winners, runners, best_thirds)

    # _build_r32 returns a flat list[str] of 32 team codes (16 matches x 2 slots)
    assert len(r32) == 32
    assert len(set(r32)) == 32

    # Build team → group reverse map
    team_group: dict[str, str] = {}
    for g, t in winners.items():
        team_group[t] = g
    for g, t in runners.items():
        team_group[t] = g
    for g, t in best_thirds.items():
        team_group[t] = g

    # No adjacent pair (i, i+1 where i is even) may share a group
    for i in range(0, 32, 2):
        t1, t2 = r32[i], r32[i + 1]
        g1 = team_group.get(t1)
        g2 = team_group.get(t2)
        if g1 is not None and g2 is not None:
            assert g1 != g2, (
                f"R32 match {i // 2}: {t1} (group {g1}) vs {t2} (group {g2}) "
                "are from the same group"
            )
