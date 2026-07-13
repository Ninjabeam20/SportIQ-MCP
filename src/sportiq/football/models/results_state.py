"""Map live WC 2026 fixtures into our team-code space and partition results.

Pure functions, no I/O. The live fixtures chain returns matches keyed by full
team NAMES (e.g. "Argentina"); the simulators and Elo seed are keyed by CODES
(e.g. "ARG"). This module joins names -> codes via the ``teams`` metadata shipped
in ``wc2026.json`` (name + fifa_code, normalised), then splits each group's
six round-robin pairings into *completed* (locked, with scores) and *remaining*
(still to be Monte-Carlo'd). It also exposes a chronological list of completed
matches for the in-tournament Elo walk, and a standings derivation that backs a
keyless standings fallback.

Robustness contract: a fixture whose team names cannot be resolved to codes is
**dropped and counted**, never crashed. Explicit provider stage data decides
whether a match is a group or knockout fixture; same-group membership is only a
fallback for legacy payloads without a stage.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# Naming variants that differ from ``wc2026.json`` team names across the live
# sources. These normalise *labels*, not curated sports facts.
_NAME_ALIASES: dict[str, str] = {
    "south korea": "KOR",
    "korea republic": "KOR",
    "republic of korea": "KOR",
    "iran": "IRN",
    "ir iran": "IRN",
    "usa": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "ivory coast": "CIV",
    "cote d ivoire": "CIV",
    "cote divoire": "CIV",
    "czechia": "CZE",
    "czech republic": "CZE",
}


def _normalize(value: str) -> str:
    """Lowercase, strip accents/diacritics, drop non-alphanumerics, collapse spaces."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = "".join(c if c.isalnum() else " " for c in stripped.lower())
    return " ".join(cleaned.split())


def build_code_index(teams_meta: dict[str, dict]) -> dict[str, str]:
    """Return {normalized_name_or_code: team_code} for resolving live team names.

    Indexes each team's ``name``, ``fifa_code`` and the code itself, plus the
    shared alias table. Used by :func:`resolve_code`.
    """
    index: dict[str, str] = {}
    for norm, code in _NAME_ALIASES.items():
        index[norm] = code
    for code, meta in teams_meta.items():
        index[_normalize(code)] = code
        name = meta.get("name")
        if name:
            index[_normalize(name)] = code
        fifa = meta.get("fifa_code")
        if fifa:
            index[_normalize(fifa)] = code
    return index


def resolve_code(name: str, index: dict[str, str]) -> str | None:
    """Resolve a live team name to a team code, or None if unmatched."""
    return index.get(_normalize(name))


def _round_robin_pairs(teams: list[str]) -> list[tuple[str, str]]:
    return [
        (teams[i], teams[j])
        for i in range(len(teams))
        for j in range(i + 1, len(teams))
    ]


@dataclass(frozen=True)
class GroupResults:
    """Completed and still-to-play pairings for one group.

    ``completed`` entries are ``(code_a, code_b, goals_a, goals_b)``; ``remaining``
    entries are ``(code_a, code_b)`` for pairs not yet played. Together they cover
    exactly the six round-robin pairings.
    """

    completed: list[tuple[str, str, int, int]] = field(default_factory=list)
    remaining: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ResultsState:
    """Live tournament state mapped into team codes.

    ``groups`` maps each group letter to its :class:`GroupResults`. ``knockout``
    lists decided knockout ties as ``(code_a, code_b, winner_code)``.
    ``completed_chrono`` is every completed match ``(code_a, code_b, goals_a,
    goals_b)`` in date order (for the Elo walk). ``matched`` / ``dropped`` count
    how many finished fixtures were resolved vs. skipped.
    """

    groups: dict[str, GroupResults] = field(default_factory=dict)
    knockout: list[tuple[str, str, str]] = field(default_factory=list)
    completed_chrono: list[tuple[str, str, int, int]] = field(default_factory=list)
    matched: int = 0
    dropped: int = 0


# Finished-match status markers across the fixture sources. football-data.org and
# openfootball emit "FINISHED"; api-football emits the short code ("FT", and "AET"/
# "PEN" after extra time / shootout). We must gate on these and NOT merely on
# "scores present" — an in-play match also carries a (live) score that must never
# be locked in as final.
_FINISHED_STATUSES = frozenset({"FINISHED", "FT", "AET", "PEN", "AWD", "WO"})


def _is_finished(fx: dict) -> bool:
    return (
        str(fx.get("status", "")).upper() in _FINISHED_STATUSES
        and fx.get("home_goals") is not None
        and fx.get("away_goals") is not None
    )


def _stage_class(
    stage: object,
    a: str,
    b: str,
    code_to_group: dict[str, str],
) -> str:
    """Classify a provider stage, falling back to draw membership when absent."""
    value = _normalize(str(stage or ""))
    if value:
        tokens = value.split()
        if "group" in tokens or "matchday" in tokens:
            return "group"
        return "knockout"
    same_group = code_to_group.get(a) is not None and code_to_group.get(a) == code_to_group.get(b)
    return "group" if same_group else "knockout"


def build_results_state(
    fixtures: list[dict],
    groups: dict[str, list[str]],
    teams_meta: dict[str, dict],
) -> ResultsState:
    """Partition live fixtures into locked group results, knockout results, etc.

    Args:
        fixtures: ``fixtures`` list from ``football_fixtures_chain`` (full team
            names, ``status``/``home_goals``/``away_goals``).
        groups: ``{group_letter: [4 team codes]}`` from the groups chain.
        teams_meta: ``{code: {name, fifa_code}}`` from the groups chain.

    Returns:
        A :class:`ResultsState`. Unmatched finished fixtures are counted in
        ``dropped`` and otherwise ignored.
    """
    index = build_code_index(teams_meta)
    code_to_group = {code: letter for letter, codes in groups.items() for code in codes}

    # Per provider match ID keep one report; legacy payloads without an ID are
    # deduplicated by stage class + pairing. The latest report by date wins.
    # Values hold (code_a, code_b, goals_a, goals_b, date, stage_class, winner).
    record: dict[
        tuple[str, object], tuple[str, str, int, int, str, str, str | None]
    ] = {}
    dropped = 0

    for fx in fixtures:
        if not _is_finished(fx):
            continue
        a = resolve_code(fx.get("home") or "", index)
        b = resolve_code(fx.get("away") or "", index)
        if a is None or b is None or a == b:
            dropped += 1
            continue
        ga = int(fx["home_goals"])
        gb = int(fx["away_goals"])
        date = fx.get("date") or ""
        pair = frozenset((a, b))
        stage_class = _stage_class(fx.get("stage"), a, b, code_to_group)
        if stage_class == "group" and (
            code_to_group.get(a) is None or code_to_group.get(a) != code_to_group.get(b)
        ):
            dropped += 1
            continue
        winner = resolve_code(fx.get("winner") or "", index)
        if winner not in pair:
            winner = None
        if stage_class == "knockout":
            winner = winner or (a if ga > gb else b if gb > ga else None)
            if winner is None:
                dropped += 1  # level knockout score with no shootout winner
                continue
        match_id = fx.get("match_id")
        key: tuple[str, object] = (
            ("id", match_id)
            if match_id is not None and match_id != ""
            else (stage_class, pair)
        )
        if key in record and date < record[key][4]:
            continue  # older report of a pairing we already have
        record[key] = (a, b, ga, gb, date, stage_class, winner)

    completed_by_group: dict[str, dict[frozenset[str], tuple[str, str, int, int]]] = {
        letter: {} for letter in groups
    }
    knockout: list[tuple[str, str, str]] = []
    chrono: list[tuple[str, str, int, int, str]] = []
    for a, b, ga, gb, date, stage_class, winner in record.values():
        chrono.append((a, b, ga, gb, date))
        if stage_class == "group":
            completed_by_group[code_to_group[a]][frozenset((a, b))] = (a, b, ga, gb)
        else:
            knockout.append((a, b, winner))

    group_states: dict[str, GroupResults] = {}
    for letter, codes in groups.items():
        played = completed_by_group[letter]
        completed = list(played.values())
        remaining = [
            (x, y) for (x, y) in _round_robin_pairs(codes) if frozenset((x, y)) not in played
        ]
        group_states[letter] = GroupResults(completed=completed, remaining=remaining)

    chrono.sort(key=lambda t: t[4])  # ascending by ISO date
    completed_chrono = [(a, b, ga, gb) for (a, b, ga, gb, _d) in chrono]

    return ResultsState(
        groups=group_states,
        knockout=knockout,
        completed_chrono=completed_chrono,
        matched=len(record),
        dropped=dropped,
    )


def derived_standings(
    fixtures: list[dict],
    groups: dict[str, list[str]],
    teams_meta: dict[str, dict],
) -> dict:
    """Compute group standings from completed fixtures — backs a keyless fallback.

    Returns ``{"standings": [{rank, team, group, points, played, goals_diff}],
    "source": "derived_standings"}`` ordered within each group by points -> GD ->
    GF. ``team`` is the human-readable name (matching the live adapters' shape).
    """
    state = build_results_state(fixtures, groups, teams_meta)
    name_of = {code: meta.get("name", code) for code, meta in teams_meta.items()}

    standings: list[dict] = []
    for letter, codes in groups.items():
        pts = dict.fromkeys(codes, 0)
        gf = dict.fromkeys(codes, 0)
        ga = dict.fromkeys(codes, 0)
        played = dict.fromkeys(codes, 0)
        for a, b, sa, sb in state.groups[letter].completed:
            played[a] += 1
            played[b] += 1
            gf[a] += sa
            gf[b] += sb
            ga[a] += sb
            ga[b] += sa
            if sa > sb:
                pts[a] += 3
            elif sb > sa:
                pts[b] += 3
            else:
                pts[a] += 1
                pts[b] += 1
        ranked = sorted(
            codes, key=lambda c: (pts[c], gf[c] - ga[c], gf[c]), reverse=True
        )
        for rank, code in enumerate(ranked, start=1):
            standings.append(
                {
                    "rank": rank,
                    "team": name_of[code],
                    "group": letter,
                    "points": pts[code],
                    "played": played[code],
                    "goals_diff": gf[code] - ga[code],
                }
            )
    return {"standings": standings, "source": "derived_standings"}
