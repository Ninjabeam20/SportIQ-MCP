"""Build cricket model seeds from Cricsheet IPL ball-by-ball JSON.

Same offline-seed lineage as ``elo_seed.json`` / ``circuits.json``: raw Cricsheet
data lives only in ``datasets/ipl_json/`` (gitignored); this derives small,
committed seeds the cricket models read. We ship only **derived aggregates**
(facts/statistics), never the raw match database — Cricsheet's match data carries
no explicit license, so aggregate-only + attribution is the community-standard
posture (see docs/wiki/data-sources/cricsheet.md).

Currently produces:
  * venues.json regeneration — measured avg 1st/2nd-innings totals per current IPL
    venue, replacing hand-eyeballed numbers. Preserves the hand-set qualitative
    ``pitch_type`` label and the ``boundary_size_m`` field (neither is in
    Cricsheet); thin-sample venues (< MIN_SAMPLE matches) keep their hand-set
    numbers untouched rather than adopt noisy averages.

NOT produced here (deliberately deferred):
  * matchups.json (batter-vs-bowler H2H) — blocked on name reconciliation:
    Cricsheet uses scorecard initials ("AD Russell") while squads.json uses mixed
    full names ("Andre Russell"); only ~13% match exactly. A clean join would need
    a hand-curated 194-name alias table, which conflicts with the project's
    "no hand-curated player-history data" constraint. See the data-source wiki page.
  * win-model logistic calibration — its own gated phase (reliability curve first).

Download once (NOT a runtime dep):

    mkdir -p datasets && curl -sSL -o datasets/ipl_json.zip \\
        https://cricsheet.org/downloads/ipl_json.zip
    unzip -oq datasets/ipl_json.zip -d datasets/ipl_json

Run:

    uv run python scripts/build_cricket_priors.py

Cricsheet credit lives in the README "Data sources & credits".
"""
from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IPL = ROOT / "datasets" / "ipl_json"
VENUES = ROOT / "src" / "sportiq" / "cricket" / "data" / "venues.json"

# Seasons that reflect current scoring norms. IPL totals have risen materially;
# pre-2018 venue averages understate the modern game.
SEASONS = {"2018", "2019", "2020/21", "2021", "2022", "2023", "2024", "2025", "2026"}
# A venue needs at least this many matches in-window before its measured averages
# overwrite the hand-set seed; below it, the seed value is more trustworthy than a
# noisy small-sample mean.
MIN_SAMPLE = 12

# canonical venues.json key -> Cricsheet venue-name substrings that resolve to it.
# Multiple spellings/renamings per ground (e.g. Motera -> Narendra Modi).
VENUE_ALIAS: dict[str, list[str]] = {
    "wankhede": ["Wankhede"],
    "chinnaswamy": ["Chinnaswamy"],
    "eden_gardens": ["Eden Gardens"],
    "chepauk": ["Chidambaram", "Chepauk"],
    "kotla": ["Feroz Shah Kotla", "Arun Jaitley"],
    "narendra_modi": ["Narendra Modi", "Sardar Patel Stadium, Motera", "Motera"],
    "punjab_cricket": ["Punjab Cricket Association"],
    "rajiv_gandhi": ["Rajiv Gandhi International"],
    "sawai_mansingh": ["Sawai Mansingh"],
    "ekana": ["Ekana"],
    "dharamshala": ["Himachal Pradesh", "Dharamsala"],
    "visakhapatnam": ["ACA-VDCA", "Rajasekhara Reddy"],
    "guwahati": ["Barsapara"],
    "indore": ["Holkar"],
}


def _canon(venue: str) -> str | None:
    for key, subs in VENUE_ALIAS.items():
        if any(s in venue for s in subs):
            return key
    return None


def _innings_total(innings: dict) -> int:
    return sum(d["runs"]["total"] for ov in innings["overs"] for d in ov["deliveries"])


# "season" sits in the info block near the top of every Cricsheet file; peeking the
# head avoids a full json.loads on the ~75% of files outside the season window.
_SEASON_PEEK = re.compile(r'"season"\s*:\s*"?([^",}\s]+)')


def build_venue_stats() -> tuple[dict[str, dict[str, int]], list[int]]:
    first: dict[str, list[int]] = defaultdict(list)
    second: dict[str, list[int]] = defaultdict(list)
    league_first: list[int] = []
    for f in IPL.glob("*.json"):
        text = f.read_text()
        peek = _SEASON_PEEK.search(text[:4096])
        if peek and peek.group(1) not in SEASONS:
            continue  # cheap skip — no full parse for out-of-window seasons
        match = json.loads(text)
        info = match["info"]
        if str(info.get("season")) not in SEASONS:
            continue
        key = _canon(info.get("venue", ""))
        innings = match.get("innings", [])
        if not innings:
            continue
        league_first.append(_innings_total(innings[0]))  # league par: ALL venues
        if not key:
            continue
        first[key].append(_innings_total(innings[0]))
        if len(innings) >= 2:
            second[key].append(_innings_total(innings[1]))

    stats: dict[str, dict[str, int]] = {}
    for key in VENUE_ALIAS:
        n = len(first[key])
        if n < MIN_SAMPLE:
            continue
        stats[key] = {
            "avg_first_innings": round(statistics.mean(first[key])),
            "avg_chasing": round(statistics.mean(second[key])) if second[key] else None,
            "sample_size": n,
        }
    return stats, league_first


def main() -> None:
    venues = json.loads(VENUES.read_text())
    stats, league_first = build_venue_stats()

    updated, kept = [], []
    for key, record in venues.items():
        m = stats.get(key)
        if not m or m["avg_chasing"] is None:
            kept.append(key)
            continue
        old1, old2 = record["avg_first_innings"], record["avg_chasing"]
        record["avg_first_innings"] = m["avg_first_innings"]
        record["avg_chasing"] = m["avg_chasing"]
        updated.append((key, old1, m["avg_first_innings"], old2, m["avg_chasing"], m["sample_size"]))

    VENUES.write_text(json.dumps(venues, indent=2) + "\n")

    league_par = round(statistics.mean(league_first))
    print(f"League T20 par (in-window 1st-innings mean, all venues): {league_par} "
          f"(n={len(league_first)}) — pitch_report._LEAGUE_PAR_T20 must match")
    print(f"Regenerated {len(updated)} venues from Cricsheet ({len(kept)} kept hand-set: {kept})")
    print(f"{'venue':16s} {'1st: was->now':>16s}  {'chase: was->now':>16s}  n")
    for key, o1, n1, o2, n2, n in sorted(updated, key=lambda r: -r[2]):
        print(f"{key:16s} {o1:>6d} -> {n1:<6d}   {o2:>6d} -> {n2:<6d}   {n}")


if __name__ == "__main__":
    main()
