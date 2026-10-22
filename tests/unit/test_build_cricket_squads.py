"""scripts/build_cricket_squads.py parse logic on two real Cricsheet IPL 2026 matches.

Fixtures in tests/fixtures/cricsheet/ are trimmed (unused info/delivery keys
dropped, registry limited to the match's players) from Cricsheet matches
1527684 (RCB v CSK, 2026-04-05) and 1529296 (LSG v CSK, 2026-05-10).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES = _ROOT / "tests" / "fixtures" / "cricsheet"


def _script():
    spec = importlib.util.spec_from_file_location(
        "build_cricket_squads", _ROOT / "scripts" / "build_cricket_squads.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed() -> dict:
    matches = [json.loads((_FIXTURES / f"{m}.json").read_text()) for m in ("1527684", "1529296")]
    return _script().parse_matches(matches)


def test_build_cricket_squads_keys_franchises_by_ipl_code():
    seed = _seed()
    assert sorted(k for k in seed if k != "_meta") == ["CSK", "LSG", "RCB"]
    assert seed["_meta"]["season"] == "2026"
    assert seed["_meta"]["credits_source"] == "formula"


def test_build_cricket_squads_carries_registry_ids():
    seed = _seed()
    kohli = next(p for p in seed["RCB"] if p["name"] == "V Kohli")
    assert kohli["player_id"] == "ba607b88"


def test_build_cricket_squads_infers_roles():
    by_name = {p["name"]: p["role"] for code in ("CSK", "LSG", "RCB") for p in _seed()[code]}
    assert by_name["JM Sharma"] == "WK-BAT"  # named on a stumping
    assert by_name["B Kumar"] == "BOWL"
    assert by_name["V Kohli"] == "BAT"
    assert by_name["S Dube"] == "ALL"


def test_build_cricket_squads_credits_in_range_and_steps():
    seed = _seed()
    for code in ("CSK", "LSG", "RCB"):
        for p in seed[code]:
            assert 7.0 <= p["credits"] <= 11.0
            assert (p["credits"] * 2) == int(p["credits"] * 2)


def test_build_cricket_squads_is_deterministic():
    assert json.dumps(_seed(), sort_keys=True) == json.dumps(_seed(), sort_keys=True)
