"""Regenerate the groups/teams in src/sportiq/football/data/wc2026.json from
football-data.org — the same source the live fixtures chain uses, so seed team
names/codes always join cleanly against live results.

The original seed was authored before qualification concluded and drifted from
the real draw (wrong teams AND wrong group composition), which silently broke
live-result conditioning: finished fixtures with unknown names were dropped and
real group matches were misclassified as knockout ties. No sports facts are
hand-curated here — everything comes from the API.

Requires FOOTBALLDATA_KEY (one request against the 100/day budget). The
``format`` block is preserved as-is; ``elo_seed.json`` is NOT touched — teams
absent from it start at the 1500 default and the in-tournament Elo walk
(elo_live.py) adjusts them from real results.

    uv run python scripts/build_wc2026_teams.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "sportiq" / "football" / "data" / "wc2026.json"


def main() -> None:
    key = os.environ.get("FOOTBALLDATA_KEY", "")
    if not key:
        sys.exit("FOOTBALLDATA_KEY is not set (source .env first)")

    resp = httpx.get(
        "https://api.football-data.org/v4/competitions/WC/standings",
        headers={"X-Auth-Token": key},
        timeout=30,
    )
    resp.raise_for_status()
    standings = [s for s in resp.json()["standings"] if s.get("type") == "TOTAL"]

    groups: dict[str, list[str]] = {}
    teams: dict[str, dict[str, str]] = {}
    for s in standings:
        letter = s["group"].replace("GROUP_", "").replace("Group ", "").strip()
        codes = []
        for row in s["table"]:
            team = row["team"]
            code = team["tla"]
            codes.append(code)
            teams[code] = {"name": team["name"], "fifa_code": code}
        groups[letter] = sorted(codes)

    assert len(groups) == 12, f"expected 12 groups, got {len(groups)}"
    assert all(len(c) == 4 for c in groups.values()), "every group must have 4 teams"
    assert len(teams) == 48, f"expected 48 teams, got {len(teams)}"

    seed = json.loads(OUT.read_text())
    seed["groups"] = dict(sorted(groups.items()))
    seed["teams"] = dict(sorted(teams.items()))
    OUT.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUT}: 12 groups, 48 teams")


if __name__ == "__main__":
    main()
