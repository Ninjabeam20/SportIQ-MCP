# C1 — Official FIFA Bracket Seeding for `football_simulate_bracket`

**Status:** Design — awaiting user review
**Date:** 2026-05-30
**Item:** C1 (remaining.md §C) — "bracket seeding is strength-based, not the official FIFA table"
**Severity:** 🟠 correctness

---

## Problem

`src/sportiq/football/models/bracket_sim.py` currently builds the 32-team knockout by
**globally re-seeding all qualifiers by simulated strength** every iteration:

```python
# bracket_sim.py:78-82  (the bug)
seeded = sorted(qualifiers, key=lambda r: (r["points"], r["gd"], r["gf"], rng.random()), reverse=True)
seed_team = {s: seeded[s - 1]["team"] for s in range(1, len(seeded) + 1)}
current = [seed_team[s] for s in _seed_order(len(seeded))]
```

This collapses the real bracket structure: group winners, runners-up, and best-thirds are
sorted into one 1-vs-32 ladder, so the **official group-position-based R32 pairings and the
fixed knockout tree are ignored**. The simulated probabilities therefore don't reflect the
actual draw paths teams face.

## Goal

Replace the global strength-reseed with the **official FIFA 2026 knockout structure**:
the fixed R32 slot template (matches 73–88), the 495-row Annex C best-thirds allocation
table, and the fixed R16→Final match-feed tree — all sourced from validated data.

## Data sources (validated, in `fifa_data/`)

All files are internally consistent and verified this session:

| File | Use |
| :--- | :--- |
| `r32_template.csv` | 16 R32 matches (`match_number,slot1,slot2`); third slots like `3A/B/C/D/F` |
| `r16_template.csv`, `qf_template.csv`, `sf_template.csv`, `third_place_match.csv`, `final.csv` | Knockout match-feed tree (`W74`, `W89`, `L101`, …) |
| `best_third_allocation.csv` | 495 rows, header `combination,slot_1A,slot_1B,slot_1D,slot_1E,slot_1G,slot_1I,slot_1K,slot_1L`; values are bare group letters |

**Validated:** allocation = 495 distinct combinations = C(12,8); every row is a bijection
(8 assigned third-groups == the qualifying-group set), no slot is paired with a third from
its own group. R32 winner-slots facing thirds = `{A,B,D,E,G,I,K,L}`; winner-slots facing
runners-up = `{C,F,H,J}`.

**No draw swap needed.** `fifa_data/group_draw.csv` and `ratings.csv` are identical to the
existing `wc2026.json` + `elo_seed.json` (same 48 teams, same Elo). The representative draw
already equals the provided data; this work touches only the *seeding*, which is positional
(`1A`, `3E`) and therefore draw-agnostic.

## Architecture

```
fifa_data/*.csv  ──(scripts/build_wc2026_bracket.py, run once, committed output)──▶
    src/sportiq/football/data/wc2026_bracket.json  ──(loaded at import)──▶  bracket_sim.py
```

### `wc2026_bracket.json` schema

```jsonc
{
  "r32": {
    "73": {"slot1": "2A", "slot2": "2B"},
    "74": {"slot1": "1E", "slot2": "3A/B/C/D/F"},
    ...                                              // 16 entries, matches 73-88
  },
  "bracket_order": [74,77,73,75,83,84,81,82,76,78,79,80,86,88,85,87],  // R32 leaf order; adjacent pairs feed the official R16/QF/SF tree
  "winner_third_slots": ["1A","1B","1D","1E","1G","1I","1K","1L"],     // slot order of the allocation columns
  "third_allocation": {
    "ABCDEFGH": {"1A":"H","1B":"G","1D":"B","1E":"C","1G":"A","1I":"F","1K":"D","1L":"E"},
    ...                                              // 495 entries, key = sorted qualifying-group string; value maps winner slot → third's group letter
  }
}
```

`bracket_order` is derived depth-first from the R16/QF/SF/final templates so that the
existing "pair adjacent, recurse" round loop reproduces the official tree with **no change to
the playing logic** — only the initial 32-team ordering changes.

### Engine changes (`bracket_sim.py`)

1. **Load** `wc2026_bracket.json` once at module import (mirroring how ratings are loaded).
2. `_simulate_once` **retains group letter** per qualifier:
   - `winners: dict[group_letter, team]`, `runners: dict[group_letter, team]`.
   - `thirds`: list of standings rows that already carry their group letter (add it in the loop).
3. Compute the **8 best thirds** (existing ranking: points → gd → gf → random), take their
   group letters, sort → `"".join(sorted(letters))` → look up `third_allocation`.
   This yields, for each winner-slot in `winner_third_slots`, the group letter of the third it faces.
4. **Resolve every slot code** to a team:
   - `1X` → `winners[X]`, `2X` → `runners[X]`.
   - A `3.../`-style slot is always paired (in its R32 match) with a winner slot `1Y` where
     `Y ∈ winner_third_slots`. Its team is `thirds_by_group[ allocation[combo][1Y] ]` — i.e.
     look up the group letter the allocation assigned to that match's winner slot, then take
     that group's third-placed team.
5. Build `current` (32 teams) by walking `bracket_order` and appending `[slot1_team, slot2_team]`
   of each R32 match.
6. Play the existing round loop unchanged (`_knockout_winner`, adjacent pairing).
7. **Delete** the global reseed and `_seed_order` (no longer used).

The group-letter must reach `_simulate_once`. `simulate_group_once` already returns rows
without a group key, so `_simulate_once` will tag each group's standings with its letter when
iterating `groups.items()`.

## Edge cases

- **Fewer/more than 8 thirds:** there are always exactly 12 thirds (one per group); top-8 is
  always well-defined. Assert `len(best_thirds) == 8`.
- **Combination key miss:** every set of 8 distinct group letters from 12 is one of the 495
  keys. Add a defensive `KeyError`→clear error if a key is missing (would indicate a data bug).
- **Determinism:** RNG threading is unchanged; same `seed` ⇒ same bracket. Preserved.

## Test plan (`tests/unit/`)

New `tests/unit/test_bracket_seeding.py`:

1. `test_bracket_data_allocation_is_complete` — 495 entries; each key 8 distinct letters;
   each value a bijection onto the key set; no slot paired with its own group's third.
2. `test_bracket_order_reproduces_official_tree` — pairing `bracket_order` adjacently and
   recursing reproduces the R16/QF/SF/final templates from the CSVs (e.g. R16 winner of the
   pair {74,77} corresponds to template match 89).
3. `test_r32_no_intra_group_winner_runner_match` — for all 16 template matches, `1X`/`2X`
   slot pairs never share a group letter.
4. `test_simulate_once_uses_official_r32_pairings` — with a stubbed RNG / fixed seed, the R32
   matchups produced match the template's group-position slots (not a strength ladder).

Existing `tests/unit/` bracket tests (32 qualifiers/iter, one champion/iter, monotone round
probabilities, determinism, ±2% convergence) MUST stay green unchanged.

## Build script

`scripts/build_wc2026_bracket.py` — reads the six template CSVs + allocation CSV from
`docs/raw/fifa_data/`, validates them (same asserts as test 1), and writes
`src/sportiq/football/data/wc2026_bracket.json`. Run once; output committed. Kept for
reproducibility, not run in CI.

Source CSVs move `fifa_data/` → `docs/raw/fifa_data/` (the immutable-source location per
wiki-conventions; `docs/raw/` is read-only input the build script consumes).

## Docs

- Update `docs/wiki/models/bracket-sim.md`: seeding is now the official FIFA template + Annex C
  allocation, not strength-based.
- Update ADR-0008 "Consequences" — the bracket-seeding simplification is resolved.
- Add `docs/index.md` nothing new (no new page); add a `docs/log.md` entry.

## Out of scope

- Real-draw adoption (unnecessary — already equals existing data).
- Group-stage fair-play / head-to-head tiebreakers (`group_standings_logic.md`) — `group_sim`
  keeps its current points→gd→gf→random ranking. Separate item if desired.
- Any other remaining.md item.
