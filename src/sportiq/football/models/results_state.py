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
from dataclasses import dataclass, field, replace

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
    # openfootball spells these differently from the draw ("Cape Verde Islands",
    # "Congo DR"). Keys are _normalize() output, so "DR. Congo" also hits "dr congo".
    "cape verde": "CPV",
    "cabo verde": "CPV",
    "dr congo": "COD",
    "congo dr": "COD",
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
    return [(teams[i], teams[j]) for i in range(len(teams)) for j in range(i + 1, len(teams))]


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
    how many finished fixtures were resolved vs. skipped. ``champion`` is the
    winner of a finished fixture whose stage is the final, else None.
    ``knockout_rounds`` maps each decided tie's pair to its round (``r32`` |
    ``r16`` | ``qf`` | ``sf`` | ``third`` | ``final``) when the provider's stage
    label names one; unlabelled ties are absent.
    """

    groups: dict[str, GroupResults] = field(default_factory=dict)
    knockout: list[tuple[str, str, str]] = field(default_factory=list)
    completed_chrono: list[tuple[str, str, int, int]] = field(default_factory=list)
    matched: int = 0
    dropped: int = 0
    champion: str | None = None
    knockout_rounds: dict[frozenset[str], str] = field(default_factory=dict)


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


def _knockout_round(stage: object) -> str | None:
    """Map a provider knockout stage label to a round id, or None if unrecognised.

    Covers openfootball ("Round of 32", "Quarter-final", "Match for third place"),
    football-data.org ("LAST_32", "QUARTER_FINALS", "THIRD_PLACE") and
    api-football ("Round of 16", "Semi-finals", "3rd Place Final").
    """
    value = _normalize(str(stage or ""))
    if not value:
        return None
    if "third" in value or "3rd" in value:
        return "third"
    if "semi" in value:
        return "sf"
    if "quarter" in value:
        return "qf"
    if value in ("round of 32", "last 32", "1 16 final", "1 16 finals"):
        return "r32"
    if value in ("round of 16", "last 16", "1 8 final", "1 8 finals"):
        return "r16"
    if value == "final" or value == "finals":
        return "final"
    return None


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
    # Values hold (code_a, code_b, goals_a, goals_b, date, stage_class, winner, ko_round).
    record: dict[
        tuple[str, object], tuple[str, str, int, int, str, str, str | None, str | None]
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
            ("id", match_id) if match_id is not None and match_id != "" else (stage_class, pair)
        )
        if key in record and date < record[key][4]:
            continue  # older report of a pairing we already have
        ko_round = _knockout_round(fx.get("stage")) if stage_class == "knockout" else None
        record[key] = (a, b, ga, gb, date, stage_class, winner, ko_round)

    completed_by_group: dict[str, dict[frozenset[str], tuple[str, str, int, int]]] = {
        letter: {} for letter in groups
    }
    knockout: list[tuple[str, str, str]] = []
    chrono: list[tuple[str, str, int, int, str]] = []
    champion: str | None = None
    knockout_rounds: dict[frozenset[str], str] = {}
    for a, b, ga, gb, date, stage_class, winner, ko_round in record.values():
        chrono.append((a, b, ga, gb, date))
        if stage_class == "group":
            completed_by_group[code_to_group[a]][frozenset((a, b))] = (a, b, ga, gb)
        else:
            knockout.append((a, b, winner))
            if ko_round is not None:
                knockout_rounds[frozenset((a, b))] = ko_round
            if ko_round == "final":
                champion = winner

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
        champion=champion,
        knockout_rounds=knockout_rounds,
    )


# Replay stages in tournament order. "Replay from X" keeps every real result
# played before X and simulates X onward.
REPLAY_STAGES: tuple[str, ...] = ("group", "r32", "r16", "qf", "sf", "final")


def truncate_results_state(state: ResultsState, keep_before: str) -> ResultsState:
    """Return a new state holding only the real results played before ``keep_before``.

    ``keep_before`` is one of :data:`REPLAY_STAGES`. ``"group"`` keeps nothing
    (a full pre-tournament replay); ``"r32"`` keeps the group stage; ``"qf"`` keeps
    the groups plus the R32 and R16 ties; and so on. Dropped group results move
    back to ``remaining``. Knockout ties without a recognised round label, and the
    third-place match, are never kept. ``completed_chrono`` (the live-Elo walk) is
    trimmed to the kept matches; ``champion`` is cleared because the final is
    never kept.

    Raises:
        ValueError: ``keep_before`` is not a replay stage.
    """
    if keep_before not in REPLAY_STAGES:
        raise ValueError(f"replay stage must be one of {', '.join(REPLAY_STAGES)}")
    cut = REPLAY_STAGES.index(keep_before)
    kept_rounds = set(REPLAY_STAGES[1:cut])  # knockout rounds strictly before the cut
    keep_groups = cut > 0

    groups: dict[str, GroupResults] = {}
    for letter, g in state.groups.items():
        if keep_groups:
            groups[letter] = GroupResults(completed=list(g.completed), remaining=list(g.remaining))
        else:
            replayed = [(a, b) for (a, b, _ga, _gb) in g.completed]
            groups[letter] = GroupResults(completed=[], remaining=replayed + list(g.remaining))

    knockout = [
        (a, b, w)
        for (a, b, w) in state.knockout
        if state.knockout_rounds.get(frozenset((a, b))) in kept_rounds
    ]
    rounds = {frozenset((a, b)): state.knockout_rounds[frozenset((a, b))] for a, b, _w in knockout}

    # Multiset of kept pairings: a pair can occur once in a group and again in a knockout.
    wanted: dict[frozenset[str], int] = {}
    for g in groups.values():
        for a, b, _ga, _gb in g.completed:
            wanted[frozenset((a, b))] = wanted.get(frozenset((a, b)), 0) + 1
    for a, b, _w in knockout:
        wanted[frozenset((a, b))] = wanted.get(frozenset((a, b)), 0) + 1
    chrono: list[tuple[str, str, int, int]] = []
    for a, b, ga, gb in state.completed_chrono:
        pair = frozenset((a, b))
        if wanted.get(pair, 0) > 0:
            wanted[pair] -= 1
            chrono.append((a, b, ga, gb))

    return replace(
        state,
        groups=groups,
        knockout=knockout,
        completed_chrono=chrono,
        matched=len(chrono),
        champion=None,
        knockout_rounds=rounds,
    )


# Decided ties per knockout round in the 48-team format (12 groups → R32).
KNOCKOUT_ROUND_SIZES: dict[str, int] = {"r32": 16, "r16": 8, "qf": 4, "sf": 2}


def results_complete_before(state: ResultsState, keep_before: str) -> bool:
    """True when ``state`` holds every real result played before ``keep_before``.

    ``"group"`` needs nothing. Later stages need every group match completed and
    every tie of each earlier knockout round decided with its round label — so a
    fixture feed without scores (e.g. the static seed) never passes for "final".

    Raises:
        ValueError: ``keep_before`` is not a replay stage.
    """
    if keep_before not in REPLAY_STAGES:
        raise ValueError(f"replay stage must be one of {', '.join(REPLAY_STAGES)}")
    cut = REPLAY_STAGES.index(keep_before)
    if cut == 0:
        return True
    if not state.groups or any(g.remaining for g in state.groups.values()):
        return False
    counts: dict[str, int] = {}
    for a, b, _w in state.knockout:
        rnd = state.knockout_rounds.get(frozenset((a, b)))
        if rnd is not None:
            counts[rnd] = counts.get(rnd, 0) + 1
    return all(counts.get(r, 0) >= KNOCKOUT_ROUND_SIZES[r] for r in REPLAY_STAGES[1:cut])


def flip_knockout_winner(state: ResultsState, code_a: str, code_b: str) -> ResultsState:
    """Return a new state where the decided knockout tie ``code_a``-``code_b`` went the other way.

    Only the locked winner changes; the recorded goals (and so the live-Elo walk)
    stay as played. Raises ``ValueError`` when that tie is not in ``state.knockout``.
    """
    pair = frozenset((code_a, code_b))
    knockout = list(state.knockout)
    for i, (a, b, winner) in enumerate(knockout):
        if frozenset((a, b)) == pair:
            flipped = b if winner == a else a
            knockout[i] = (a, b, flipped)
            champion = flipped if state.knockout_rounds.get(pair) == "final" else state.champion
            return replace(state, knockout=knockout, champion=champion)
    raise ValueError(f"{code_a}-{code_b} is not a decided knockout tie in the kept results.")


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
        ranked = sorted(codes, key=lambda c: (pts[c], gf[c] - ga[c], gf[c]), reverse=True)
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
