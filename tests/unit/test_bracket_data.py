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
