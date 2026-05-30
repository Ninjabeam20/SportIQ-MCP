"""Build src/sportiq/football/data/wc2026_bracket.json from docs/raw/fifa_data CSVs.

Run once (output committed); kept for reproducibility. Not run in CI.

    uv run python scripts/build_wc2026_bracket.py
"""
from __future__ import annotations

import csv
import json
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs" / "raw" / "fifa_data"
OUT = ROOT / "src" / "sportiq" / "football" / "data" / "wc2026_bracket.json"

# Winner slots that face a third-placed team, in the column order of the allocation CSV.
WINNER_THIRD_SLOTS = ["1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L"]


def _rows(name: str) -> list[dict]:
    with (RAW / name).open() as f:
        return list(csv.DictReader(f))


def build_r32() -> dict[str, dict]:
    out = {}
    for r in _rows("r32_template.csv"):
        out[r["match_number"]] = {"slot1": r["slot1"], "slot2": r["slot2"]}
    assert len(out) == 16, f"expected 16 R32 matches, got {len(out)}"
    return out


def build_bracket_order() -> list[int]:
    """Depth-first leaf order of the official tree, so adjacent R32 pairs feed the right R16."""
    feeds: dict[int, tuple[int, int]] = {}
    for name in ("r16_template.csv", "qf_template.csv", "sf_template.csv", "final.csv"):
        for r in _rows(name):
            feeds[int(r["match"])] = (int(r["slot1"][1:]), int(r["slot2"][1:]))

    def leaves(m: int) -> list[int]:
        if m not in feeds:  # an R32 match number
            return [m]
        a, b = feeds[m]
        return leaves(a) + leaves(b)

    order = leaves(104)  # final
    assert sorted(order) == list(range(73, 89)), f"bracket_order not the 16 R32 matches: {order}"
    return order


def build_allocation() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for r in _rows("best_third_allocation.csv"):
        combo = r["combination"]
        alloc = {s: r[f"slot_{s}"] for s in WINNER_THIRD_SLOTS}
        # Validate: bijection between assigned third-groups and the qualifying set; no self-group.
        assert set(alloc.values()) == set(combo), f"{combo}: values {alloc} != combo set"
        assert len(set(alloc.values())) == 8, f"{combo}: duplicate third assignment"
        for slot, grp in alloc.items():
            assert slot[1] != grp, f"{combo}: slot {slot} faces its own group's third {grp}"
        out[combo] = alloc
    assert len(out) == comb(12, 8) == 495, f"expected 495 combinations, got {len(out)}"
    return out


def main() -> None:
    data = {
        "r32": build_r32(),
        "bracket_order": build_bracket_order(),
        "winner_third_slots": WINNER_THIRD_SLOTS,
        "third_allocation": build_allocation(),
    }
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {OUT} ({len(data['third_allocation'])} allocation rows)")


if __name__ == "__main__":
    main()
