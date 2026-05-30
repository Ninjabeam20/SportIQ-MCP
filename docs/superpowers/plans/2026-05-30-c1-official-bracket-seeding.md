# C1 — Official FIFA Bracket Seeding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the global strength-reseed in `football_simulate_bracket` with the official FIFA 2026 knockout structure (R32 slot template + 495-row Annex C best-thirds allocation + fixed R16→Final tree).

**Architecture:** Validated CSVs in `docs/raw/fifa_data/` → a one-off build script emits `src/sportiq/football/data/wc2026_bracket.json` → `bracket_sim.py` loads it at import and resolves official slot codes (`1A`/`2C`/`3…`) to teams each iteration, keeping the existing round-playing loop intact. The data loader lives **in `bracket_sim.py`** (not `static_seed.py`) because `static_seed.py` already imports `bracket_sim`, so loading there would be circular.

**Tech Stack:** Python 3.11, numpy, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-30-c1-official-bracket-seeding-design.md`

---

### Task 0: Feature branch

**Files:** none (git only)

- [ ] **Step 1: Branch off main**

Run:
```bash
git checkout -b feat/c1-official-bracket-seeding
```
Expected: `Switched to a new branch 'feat/c1-official-bracket-seeding'`

---

### Task 1: Relocate source CSVs into `docs/raw/`

**Files:**
- Move: `fifa_data/*` → `docs/raw/fifa_data/`

`docs/raw/` is the immutable-source location (wiki-conventions). The build script in Task 2 reads from there.

- [ ] **Step 1: Move the folder**

Run:
```bash
mkdir -p docs/raw && git mv fifa_data docs/raw/fifa_data 2>/dev/null || mv fifa_data docs/raw/fifa_data
ls docs/raw/fifa_data/best_third_allocation.csv docs/raw/fifa_data/r32_template.csv
```
Expected: both paths listed, no error.

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "chore: relocate fifa_data CSVs into docs/raw (immutable source)"
```

---

### Task 2: Build script → `wc2026_bracket.json`

**Files:**
- Create: `scripts/build_wc2026_bracket.py`
- Create (generated): `src/sportiq/football/data/wc2026_bracket.json`

- [ ] **Step 1: Write the build script**

Create `scripts/build_wc2026_bracket.py`:
```python
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
```

- [ ] **Step 2: Run the build script (its asserts ARE the verification)**

Run:
```bash
uv run python scripts/build_wc2026_bracket.py
```
Expected: `wrote .../wc2026_bracket.json (495 allocation rows)` and no AssertionError.

- [ ] **Step 3: Sanity-check the output shape**

Run:
```bash
uv run python -c "import json; d=json.load(open('src/sportiq/football/data/wc2026_bracket.json')); print(len(d['r32']), len(d['bracket_order']), len(d['third_allocation']), d['bracket_order']); print(d['r32']['74'], d['third_allocation']['ABCDEFGH'])"
```
Expected:
```
16 16 495 [74, 77, 73, 75, 83, 84, 81, 82, 76, 78, 79, 80, 86, 88, 85, 87]
{'slot1': '1E', 'slot2': '3A/B/C/D/F'} {'1A': 'H', '1B': 'G', '1D': 'B', '1E': 'C', '1G': 'A', '1I': 'F', '1K': 'D', '1L': 'E'}
```

- [ ] **Step 4: Commit**

```bash
git add scripts/build_wc2026_bracket.py src/sportiq/football/data/wc2026_bracket.json
git commit -m "feat: generate wc2026_bracket.json (R32 template + Annex C allocation + tree)"
```

---

### Task 3: Bracket-data integrity test

**Files:**
- Test: `tests/unit/test_bracket_data.py`

- [ ] **Step 1: Write the test**

Create `tests/unit/test_bracket_data.py`:
```python
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
```

- [ ] **Step 2: Run it (passes against the committed JSON)**

Run:
```bash
uv run pytest tests/unit/test_bracket_data.py -v
```
Expected: 4 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_bracket_data.py
git commit -m "test: bracket data integrity (495 bijective rows, 16-match tree)"
```

---

### Task 4: Refactor `bracket_sim.py` to official seeding

**Files:**
- Modify: `src/sportiq/football/models/bracket_sim.py`
- Modify: `tests/unit/test_bracket_sim.py` (drop the deleted `_seed_order` import/test)

- [ ] **Step 1: Write the failing test for official R32 pairings**

Add to `tests/unit/test_bracket_sim.py` (keep the existing invariant tests; details in Step 5):
```python
def test_r32_uses_official_group_position_pairings():
    # One deterministic tournament; collect the actual R32 matchups and confirm they are the
    # official group-position pairings (e.g. 2A vs 2B exists), not a global strength ladder.
    import numpy as np

    from sportiq.football.models import bracket_sim

    rng = np.random.default_rng(7)
    winners, runners, thirds = bracket_sim._draw_qualifiers(rng, _GROUPS, _RATINGS)
    current = bracket_sim._build_r32(winners, runners, thirds)
    assert len(current) == 32
    # Match 73 is "2A vs 2B": runners-up of A and B must be adjacent somewhere in the array.
    pairs = {(current[i], current[i + 1]) for i in range(0, 32, 2)}
    assert (runners["A"], runners["B"]) in pairs or (runners["B"], runners["A"]) in pairs
```

- [ ] **Step 2: Run it to verify it fails**

Run:
```bash
uv run pytest tests/unit/test_bracket_sim.py::test_r32_uses_official_group_position_pairings -v
```
Expected: FAIL with `AttributeError: module 'sportiq.football.models.bracket_sim' has no attribute '_draw_qualifiers'`.

- [ ] **Step 3: Rewrite `bracket_sim.py`**

Replace the entire contents of `src/sportiq/football/models/bracket_sim.py` with:
```python
"""Full-tournament Monte Carlo for WC 2026 (48 teams, 12 groups, R32 knockout).

Per iteration: simulate all 12 groups, take the top 2 of each plus the 8 best
third-placed teams (32 qualifiers), slot them into the **official FIFA 2026
knockout structure** (R32 template + Annex C best-thirds allocation + the fixed
R16->Final match tree, all from ``wc2026_bracket.json``), and play it to a
champion. Aggregating over many iterations yields each team's probability of
reaching every round and of winning the tournament.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sportiq.football.models.elo import expected_score
from sportiq.football.models.group_sim import simulate_group_once
from sportiq.football.models.poisson_xg import lambdas_from_elo

_STAGES = ["R32", "R16", "QF", "SF", "Final", "Winner"]
# Round labels for the 5 knockout reductions starting from 32 qualifiers.
_KO_ROUNDS = ["R16", "QF", "SF", "Final", "Winner"]

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
# Official bracket structure, loaded once at import (see scripts/build_wc2026_bracket.py).
_BRACKET = json.loads((_DATA_DIR / "wc2026_bracket.json").read_text())


def _draw_qualifiers(
    rng: np.random.Generator,
    groups: dict[str, list[str]],
    ratings: dict[str, float],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Simulate all 12 groups. Return (winners, runners, best_thirds_by_group).

    ``winners``/``runners`` map every group letter to a team. ``best_thirds_by_group``
    maps only the 8 best third-placed groups (by points -> gd -> gf -> random) to their team.
    """
    winners: dict[str, str] = {}
    runners: dict[str, str] = {}
    thirds: list[dict] = []
    for letter, teams in groups.items():
        standings = simulate_group_once(rng, teams, ratings)
        winners[letter] = standings[0]["team"]
        runners[letter] = standings[1]["team"]
        third = dict(standings[2])
        third["group"] = letter
        thirds.append(third)

    best = sorted(
        thirds, key=lambda r: (r["points"], r["gd"], r["gf"], rng.random()), reverse=True
    )[:8]
    best_thirds = {r["group"]: r["team"] for r in best}
    return winners, runners, best_thirds


def _build_r32(
    winners: dict[str, str],
    runners: dict[str, str],
    best_thirds: dict[str, str],
) -> list[str]:
    """Resolve the official R32 template to 32 teams in bracket order.

    The returned list pairs adjacent entries (0,1), (2,3), ... as R32 matches, ordered so the
    existing round loop reproduces the official R16/QF/SF/final tree.
    """
    combo = "".join(sorted(best_thirds))
    alloc = _BRACKET["third_allocation"][combo]  # {winner_slot: third_group_letter}

    def base(slot: str) -> str | None:
        if slot[0] == "1":
            return winners[slot[1]]
        if slot[0] == "2":
            return runners[slot[1]]
        return None  # a "3.../" third slot, resolved against its paired winner slot

    current: list[str] = []
    for match_no in _BRACKET["bracket_order"]:
        m = _BRACKET["r32"][str(match_no)]
        s1, s2 = m["slot1"], m["slot2"]
        t1, t2 = base(s1), base(s2)
        if t1 is None:  # s1 is the third slot; s2 is its winner slot "1Y"
            t1 = best_thirds[alloc[s2]]
        if t2 is None:  # s2 is the third slot; s1 is its winner slot "1Y"
            t2 = best_thirds[alloc[s1]]
        current.extend([t1, t2])
    return current


def _knockout_winner(
    rng: np.random.Generator,
    team_a: str,
    team_b: str,
    ratings: dict[str, float],
) -> str:
    """Decide one knockout tie. Draws after normal time go to a weighted shootout."""
    ra, rb = ratings.get(team_a, 1500.0), ratings.get(team_b, 1500.0)
    lam_a, lam_b = lambdas_from_elo(ra, rb, 0.0)
    goals_a = int(rng.poisson(lam_a))
    goals_b = int(rng.poisson(lam_b))
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    return team_a if rng.random() < expected_score(ra, rb) else team_b


def _simulate_once(
    rng: np.random.Generator,
    groups: dict[str, list[str]],
    ratings: dict[str, float],
) -> dict[str, int]:
    """One tournament. Returns ``{team: furthest_stage_index}`` for qualifiers."""
    winners, runners, best_thirds = _draw_qualifiers(rng, groups, ratings)
    current = _build_r32(winners, runners, best_thirds)

    reached: dict[str, int] = {team: 0 for team in current}  # 0 == reached R32
    for stage_idx, _round in enumerate(_KO_ROUNDS, start=1):
        nxt = []
        for k in range(0, len(current), 2):
            winner = _knockout_winner(rng, current[k], current[k + 1], ratings)
            reached[winner] = stage_idx
            nxt.append(winner)
        current = nxt
    return reached


def simulate_tournament(
    groups: dict[str, list[str]],
    ratings: dict[str, float],
    n_iter: int = 10000,
    seed: int | None = None,
) -> dict:
    """Monte Carlo the whole tournament. Returns per-team round probabilities.

    Args:
        groups: ``{group_letter: [4 team codes]}`` — the full 12-group draw.
        ratings: ``{team_code: elo}`` for every team in ``groups``.
        n_iter: iterations (10k gives stable ±2% probabilities).
        seed: RNG seed for reproducibility.

    Returns:
        ``{"teams": {code: {reach_r32, reach_r16, reach_qf, reach_sf,
        reach_final, win}}, "iterations": n, "champion": code}`` — teams sorted
        by win probability (descending).
    """
    rng = np.random.default_rng(seed)
    all_teams = [t for teams in groups.values() for t in teams]
    counts = {t: [0] * len(_STAGES) for t in all_teams}

    for _ in range(n_iter):
        reached = _simulate_once(rng, groups, ratings)
        for team, furthest in reached.items():
            for idx in range(furthest + 1):  # cumulative: reaching SF implies reaching R32..SF
                counts[team][idx] += 1

    keys = ["reach_r32", "reach_r16", "reach_qf", "reach_sf", "reach_final", "win"]
    teams_out = {
        t: {key: round(counts[t][i] / n_iter, 4) for i, key in enumerate(keys)}
        for t in all_teams
    }
    ranked = dict(sorted(teams_out.items(), key=lambda kv: kv[1]["win"], reverse=True))
    champion = next(iter(ranked))
    return {"teams": ranked, "iterations": n_iter, "champion": champion}
```

- [ ] **Step 4: Run the new pairing test to verify it passes**

Run:
```bash
uv run pytest tests/unit/test_bracket_sim.py::test_r32_uses_official_group_position_pairings -v
```
Expected: PASS.

- [ ] **Step 5: Remove the obsolete `_seed_order` import and test**

In `tests/unit/test_bracket_sim.py`, change the import line:
```python
from sportiq.football.models.bracket_sim import _seed_order, simulate_tournament
```
to:
```python
from sportiq.football.models.bracket_sim import simulate_tournament
```
and delete the whole `test_seed_order_keeps_top_seeds_apart` function (it tested a helper that no longer exists).

- [ ] **Step 6: Run the full bracket suite (all invariants stay green)**

Run:
```bash
uv run pytest tests/unit/test_bracket_sim.py -v
```
Expected: all pass (32-qualifiers, one-champion, monotone, convergence, reproducible, new pairing test).

- [ ] **Step 7: Run the football tool e2e test (envelope unaffected)**

Run:
```bash
uv run pytest tests/tools/test_football_tools.py -q
```
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/sportiq/football/models/bracket_sim.py tests/unit/test_bracket_sim.py
git commit -m "feat: official FIFA R32 seeding + Annex C allocation in bracket_sim"
```

---

### Task 5: Full suite + lint

**Files:** none (verification)

- [ ] **Step 1: Run the whole suite**

Run:
```bash
uv run pytest -q
```
Expected: all pass (was 287; now +5 from the new data/pairing tests, -1 removed seed_order test ≈ 291).

- [ ] **Step 2: Lint**

Run:
```bash
uv run ruff check src/sportiq/football/models/bracket_sim.py scripts/build_wc2026_bracket.py tests/unit/test_bracket_data.py
```
Expected: `All checks passed!`

---

### Task 6: Docs

**Files:**
- Modify: `docs/wiki/models/bracket-sim.md`
- Modify: `docs/wiki/decisions/0008-football-fallback-strategy.md`
- Modify: `docs/log.md`

- [ ] **Step 1: Update the bracket-sim wiki page**

In `docs/wiki/models/bracket-sim.md`, replace any description of "strength-seeded" / "1-vs-N bracket" knockout with: the knockout now uses the **official FIFA 2026 structure** — the R32 slot template (matches 73–88), the 495-row Annex C best-thirds allocation table, and the fixed R16→Final match tree, all encoded in `wc2026_bracket.json` (generated by `scripts/build_wc2026_bracket.py` from `docs/raw/fifa_data/`). Bump `last_updated: 2026-05-30`.

- [ ] **Step 2: Update ADR-0008 consequences**

In `docs/wiki/decisions/0008-football-fallback-strategy.md`, under "Consequences / known simplifications", change the **Bracket seeding** bullet to note it is now RESOLVED: official R32 template + Annex C allocation + fixed tree are used (see `wc2026_bracket.json`); strength-reseed removed. Leave the other simplifications intact.

- [ ] **Step 3: Append a log entry**

Append to `docs/log.md`:
```markdown
## [2026-05-30] tool-added | C1: official FIFA bracket seeding

`football_simulate_bracket` now seeds the knockout from the official FIFA 2026 structure
(R32 template + 495-row Annex C best-thirds allocation + fixed R16→Final tree) instead of a
global strength reseed. Data generated by `scripts/build_wc2026_bracket.py` from
`docs/raw/fifa_data/` into `wc2026_bracket.json`. Draw/ratings unchanged (already equal the
provided data). All invariants preserved.
```

- [ ] **Step 4: Commit**

```bash
git add docs/wiki/models/bracket-sim.md docs/wiki/decisions/0008-football-fallback-strategy.md docs/log.md
git commit -m "docs: bracket-sim official seeding (wiki + ADR-0008 + log)"
```

---

## Done criteria

- `uv run pytest -q` green; `ruff check` clean on touched files.
- `bracket_sim.py` no longer references `_seed_order` or a strength reseed.
- `git log --oneline` shows the Task 0–6 commits on `feat/c1-official-bracket-seeding`.
- **No push** (per push discipline — wait for explicit sign-off).

## Follow-ups (not in this plan)

- Real-draw adoption — unnecessary (provided draw already equals existing data).
- Group-stage fair-play / head-to-head tiebreakers (`group_standings_logic.md`) — `group_sim` keeps points→gd→gf→random. Separate item if desired.
