"""Build the bundled cricket squad seed from Cricsheet IPL ball-by-ball JSON.

Replaces the hand-written ``src/sportiq/cricket/data/squads.json`` (no hand-curated
player data). Same offline-seed lineage as ``build_cricket_priors.py``: the raw
Cricsheet archive lives only in ``datasets/`` (gitignored); this derives a small
committed seed.

A franchise's squad = every player who appeared for it in >= 1 match of SEASON,
keyed by IPL code (``cricket/teams.py``), with the Cricsheet ``registry.people`` id
as ``player_id``. Names are Cricsheet scorecard names (e.g. "TM Head").

Role inference (documented constants below; heuristics, not official roles):
  * ``WK-BAT`` if the player is named as fielder on any ``stumped`` dismissal
    (Cricsheet has no keeper field, so a keeper with no stumpings reads as BAT)
  * ``BOWL``   if legal balls bowled per match >= BOWL_MIN_BALLS_PM and
               batting runs per match < BOWL_MAX_RUNS_PM
  * ``ALL``    if balls per match >= AR_MIN_BALLS_PM and runs per match >= AR_MIN_RUNS_PM
  * else ``BAT``

Credits are a heuristic (``meta.credits_source="formula"``):
  impact = season runs + WICKET_WEIGHT * season bowler wickets
  credits = CREDIT_MIN + (CREDIT_MAX - CREDIT_MIN) * impact / max_impact,
            rounded to the nearest CREDIT_STEP.

Deterministic: sorted keys, players sorted by name, and ``generated_at`` is the
latest Cricsheet ``meta.created`` date among the season's matches (not wall-clock),
so a re-run from the same archive is byte-identical.

Download once (NOT a runtime dep; the script fetches it if missing):

    mkdir -p datasets && curl -sSL -o datasets/ipl_json.zip \\
        https://cricsheet.org/downloads/ipl_json.zip

Run:

    uv run python scripts/build_cricket_squads.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sportiq.cricket.teams import IPL_TEAM_NAMES, resolve_team_code  # noqa: E402

ZIP_PATH = ROOT / "datasets" / "ipl_json.zip"
ZIP_URL = "https://cricsheet.org/downloads/ipl_json.zip"
OUT = ROOT / "src" / "sportiq" / "cricket" / "data" / "squads.json"

SEASON = "2026"

BOWL_MIN_BALLS_PM = 12
BOWL_MAX_RUNS_PM = 15
AR_MIN_BALLS_PM = 6
AR_MIN_RUNS_PM = 10

WICKET_WEIGHT = 20
CREDIT_MIN = 7.0
CREDIT_MAX = 11.0
CREDIT_STEP = 0.5

# Dismissals not credited to the bowler.
_NON_BOWLER_WICKETS = {
    "run out",
    "retired hurt",
    "retired out",
    "retired not out",
    "obstructing the field",
}

NOTE = "IPL 2026 season appearances; 2027 retentions not reflected"


def _role(stats: dict) -> str:
    matches = stats["matches"] or 1
    balls_pm = stats["balls"] / matches
    runs_pm = stats["runs"] / matches
    if stats["stumpings"]:
        return "WK-BAT"
    if balls_pm >= BOWL_MIN_BALLS_PM and runs_pm < BOWL_MAX_RUNS_PM:
        return "BOWL"
    if balls_pm >= AR_MIN_BALLS_PM and runs_pm >= AR_MIN_RUNS_PM:
        return "ALL"
    return "BAT"


def _credits(impact: float, max_impact: float) -> float:
    if max_impact <= 0:
        return CREDIT_MIN
    raw = CREDIT_MIN + (CREDIT_MAX - CREDIT_MIN) * impact / max_impact
    return round(raw / CREDIT_STEP) * CREDIT_STEP


def parse_matches(matches: Iterable[dict], season: str = SEASON) -> dict:
    """Pure parse: Cricsheet match dicts → the squads seed (``_meta`` + codes)."""
    stats: dict[str, dict] = defaultdict(
        lambda: {"matches": 0, "runs": 0, "balls": 0, "wickets": 0, "stumpings": 0}
    )
    appearances: dict[str, set[str]] = defaultdict(set)
    people: dict[str, str] = {}
    created: list[str] = []

    for match in matches:
        info = match.get("info", {})
        if str(info.get("season")) != season:
            continue
        created.append(str((match.get("meta") or {}).get("created", "")))
        people.update(info.get("registry", {}).get("people", {}))
        for team_name, players in info.get("players", {}).items():
            code = resolve_team_code(team_name, IPL_TEAM_NAMES)
            if code is None:
                continue
            for player in players:
                stats[player]["matches"] += 1
                appearances[code].add(player)
        for innings in match.get("innings", []):
            for over in innings.get("overs", []):
                for delivery in over.get("deliveries", []):
                    stats[delivery["batter"]]["runs"] += delivery["runs"]["batter"]
                    extras = delivery.get("extras", {})
                    if "wides" not in extras and "noballs" not in extras:
                        stats[delivery["bowler"]]["balls"] += 1
                    for wicket in delivery.get("wickets", []):
                        if wicket.get("kind") not in _NON_BOWLER_WICKETS:
                            stats[delivery["bowler"]]["wickets"] += 1
                        if wicket.get("kind") == "stumped":
                            for fielder in wicket.get("fielders", []):
                                stats[fielder["name"]]["stumpings"] += 1

    impact = {p: s["runs"] + WICKET_WEIGHT * s["wickets"] for p, s in stats.items()}
    max_impact = max(impact.values(), default=0)

    seed: dict = {
        "_meta": {
            "source": "Cricsheet IPL ball-by-ball JSON (cricsheet.org/downloads/ipl_json.zip)",
            "season": season,
            "generated_at": max(created, default=""),
            "script": "scripts/build_cricket_squads.py",
            "note": NOTE,
            "credits_source": "formula",
            "roles_source": "inferred from season appearances (see script docstring)",
        }
    }
    for code in sorted(appearances):
        seed[code] = [
            {
                "name": player,
                "player_id": people.get(player),
                "role": _role(stats[player]),
                "credits": _credits(impact[player], max_impact),
            }
            for player in sorted(appearances[code])
        ]
    return seed


def _iter_zip(path: Path) -> Iterable[dict]:
    with zipfile.ZipFile(path) as zf:
        for name in sorted(zf.namelist()):
            if name.endswith(".json"):
                yield json.loads(zf.read(name))


def main() -> None:
    if not ZIP_PATH.exists():
        ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading {ZIP_URL} → {ZIP_PATH}")
        urllib.request.urlretrieve(ZIP_URL, ZIP_PATH)  # nosec B310 — fixed https URL
    seed = parse_matches(_iter_zip(ZIP_PATH))
    OUT.write_text(json.dumps(seed, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    for code, players in seed.items():
        if code == "_meta":
            continue
        roles: dict[str, int] = defaultdict(int)
        for p in players:
            roles[p["role"]] += 1
        print(code, len(players), dict(sorted(roles.items())))
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
