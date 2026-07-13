"""Group-stage Monte Carlo for the 2026 format (4-team round-robin).

Each group plays a full round-robin (6 matches). Match scores are sampled from
the Poisson engine; standings use 3/1/0 points with FIFA-style tiebreakers
(head-to-head fields first, then available overall fields). Missing conduct and
FIFA-ranking data falls back explicitly to model rating, then RNG only when the
ratings are equal. The full-stage aggregator evaluates best thirds contextually
across all 12 groups.
"""
from __future__ import annotations

import numpy as np

from sportiq.football.models.poisson_xg import lambdas_from_elo
from sportiq.football.models.results_state import GroupResults, ResultsState

# Within a group everyone is at a neutral venue, so no home advantage.
_NEUTRAL = 0.0


def _round_robin_pairs(teams: list[str]) -> list[tuple[int, int]]:
    return [(i, j) for i in range(len(teams)) for j in range(i + 1, len(teams))]


def _completed_lookup(known: GroupResults | None) -> dict[frozenset[str], tuple[str, str, int, int]]:
    """Index a group's completed results by the unordered team pairing."""
    if known is None:
        return {}
    return {frozenset((a, b)): (a, b, ga, gb) for (a, b, ga, gb) in known.completed}


def _rank_group(
    rng: np.random.Generator,
    teams: list[str],
    ratings: dict[str, float],
    points: dict[str, int],
    gf: dict[str, int],
    ga: dict[str, int],
    matches: list[tuple[str, str, int, int]],
) -> list[dict]:
    """Rank a completed table using the available FIFA 2026 criteria."""
    ranked: list[dict] = []
    for point_total in sorted(set(points.values()), reverse=True):
        cohort = [team for team in teams if points[team] == point_total]
        h2h_points = dict.fromkeys(cohort, 0)
        h2h_gf = dict.fromkeys(cohort, 0)
        h2h_ga = dict.fromkeys(cohort, 0)
        cohort_set = set(cohort)
        for a, b, goals_a, goals_b in matches:
            if a not in cohort_set or b not in cohort_set:
                continue
            h2h_gf[a] += goals_a
            h2h_gf[b] += goals_b
            h2h_ga[a] += goals_b
            h2h_ga[b] += goals_a
            if goals_a > goals_b:
                h2h_points[a] += 3
            elif goals_b > goals_a:
                h2h_points[b] += 3
            else:
                h2h_points[a] += 1
                h2h_points[b] += 1

        available_keys = {
            team: (
                h2h_points[team],
                h2h_gf[team] - h2h_ga[team],
                gf[team],
                gf[team] - ga[team],
                gf[team],
            )
            for team in cohort
        }
        key_counts = {
            key: sum(other_key == key for other_key in available_keys.values())
            for key in set(available_keys.values())
        }
        random_keys = {team: rng.random() for team in cohort}
        cohort.sort(
            key=lambda team: (
                *available_keys[team],
                ratings.get(team, 1500.0),
                random_keys[team],
            ),
            reverse=True,
        )
        for team in cohort:
            ranked.append(
                {
                    "team": team,
                    "points": points[team],
                    "gd": gf[team] - ga[team],
                    "gf": gf[team],
                    "tiebreak_fallback": key_counts[available_keys[team]] > 1,
                }
            )

    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def _rank_thirds(
    rng: np.random.Generator,
    thirds: list[dict],
    ratings: dict[str, float],
) -> tuple[list[dict], int]:
    """Rank third-placed teams, exposing model-rating fallback usage."""
    available_keys = {
        row["team"]: (row["points"], row["gd"], row["gf"]) for row in thirds
    }
    key_counts = {
        key: sum(other_key == key for other_key in available_keys.values())
        for key in set(available_keys.values())
    }
    random_keys = {row["team"]: rng.random() for row in thirds}
    ranked = sorted(
        thirds,
        key=lambda row: (
            *available_keys[row["team"]],
            ratings.get(row["team"], 1500.0),
            random_keys[row["team"]],
        ),
        reverse=True,
    )
    fallback_rows = 0
    for row in ranked:
        fallback = key_counts[available_keys[row["team"]]] > 1
        row["third_tiebreak_fallback"] = fallback
        fallback_rows += int(fallback)
    return ranked, fallback_rows


def simulate_group_once(
    rng: np.random.Generator,
    teams: list[str],
    ratings: dict[str, float],
    known: GroupResults | None = None,
) -> list[dict]:
    """Simulate one group's round-robin. Returns standings, best-to-worst.

    Each entry includes ``team``, points/GD/GF, rank, and whether missing
    conduct/FIFA-ranking fields required the model-rating fallback.

    If ``known`` is supplied, its completed matches are locked in at their real
    scores and only the remaining pairings are sampled — so partially-played
    groups condition on reality. With ``known=None`` every match is sampled
    (the original from-scratch behaviour).
    """
    points = dict.fromkeys(teams, 0)
    gf = dict.fromkeys(teams, 0)
    ga = dict.fromkeys(teams, 0)
    locked = _completed_lookup(known)
    matches: list[tuple[str, str, int, int]] = []

    for i, j in _round_robin_pairs(teams):
        a, b = teams[i], teams[j]
        fixed = locked.get(frozenset((a, b)))
        if fixed is not None:
            ca, cb, gca, gcb = fixed
            goals_a, goals_b = (gca, gcb) if (ca, cb) == (a, b) else (gcb, gca)
        else:
            lam_a, lam_b = lambdas_from_elo(
                ratings.get(a, 1500.0), ratings.get(b, 1500.0), _NEUTRAL
            )
            goals_a = int(rng.poisson(lam_a))
            goals_b = int(rng.poisson(lam_b))
        matches.append((a, b, goals_a, goals_b))
        gf[a] += goals_a
        gf[b] += goals_b
        ga[a] += goals_b
        ga[b] += goals_a
        if goals_a > goals_b:
            points[a] += 3
        elif goals_b > goals_a:
            points[b] += 3
        else:
            points[a] += 1
            points[b] += 1

    return _rank_group(rng, teams, ratings, points, gf, ga, matches)


def draw_qualifiers_once(
    rng: np.random.Generator,
    groups: dict[str, list[str]],
    ratings: dict[str, float],
    results: ResultsState | None = None,
) -> tuple[
    dict[str, str],
    dict[str, str],
    dict[str, str],
    dict[str, list[dict]],
    int,
]:
    """Simulate every group and select the contextual eight best thirds."""
    winners: dict[str, str] = {}
    runners: dict[str, str] = {}
    thirds: list[dict] = []
    standings_by_group: dict[str, list[dict]] = {}
    fallback_rows = 0
    for letter, teams in groups.items():
        if len(teams) != 4:
            raise ValueError(
                f"Group {letter} must have exactly 4 teams (WC 2026 format); got {len(teams)}."
            )
        known = results.groups.get(letter) if results else None
        standings = simulate_group_once(rng, teams, ratings, known)
        standings_by_group[letter] = standings
        fallback_rows += sum(int(row["tiebreak_fallback"]) for row in standings)
        winners[letter] = standings[0]["team"]
        runners[letter] = standings[1]["team"]
        third = dict(standings[2])
        third["group"] = letter
        thirds.append(third)

    ranked_thirds, third_fallback_rows = _rank_thirds(rng, thirds, ratings)
    best_thirds = {row["group"]: row["team"] for row in ranked_thirds[:8]}
    return (
        winners,
        runners,
        best_thirds,
        standings_by_group,
        fallback_rows + third_fallback_rows,
    )


def simulate_group_stage(
    groups: dict[str, list[str]],
    ratings: dict[str, float],
    n_iter: int = 10000,
    seed: int | None = None,
    results: ResultsState | None = None,
) -> dict:
    """Aggregate all 12 groups plus the contextual best-third selection."""
    if len(groups) != 12:
        raise ValueError(f"simulate_group_stage expects 12 groups; got {len(groups)}.")
    all_teams = [team for teams in groups.values() for team in teams]
    position_counts = {team: [0, 0, 0, 0] for team in all_teams}
    auto_counts = dict.fromkeys(all_teams, 0)
    third_counts = dict.fromkeys(all_teams, 0)
    points_sum = dict.fromkeys(all_teams, 0)
    fallback_rows = 0
    rng = np.random.default_rng(seed)

    for _ in range(n_iter):
        _, _, best_thirds, standings_by_group, fallbacks = draw_qualifiers_once(
            rng, groups, ratings, results
        )
        selected_thirds = set(best_thirds.values())
        fallback_rows += fallbacks
        for standings in standings_by_group.values():
            for row in standings:
                team = row["team"]
                position_counts[team][row["rank"] - 1] += 1
                points_sum[team] += row["points"]
                if row["rank"] <= 2:
                    auto_counts[team] += 1
                elif row["rank"] == 3 and team in selected_thirds:
                    third_counts[team] += 1

    teams_out = {}
    for team in all_teams:
        positions = position_counts[team]
        auto = auto_counts[team] / n_iter
        best_third = third_counts[team] / n_iter
        auto_rounded = round(auto, 4)
        best_third_rounded = round(best_third, 4)
        teams_out[team] = {
            "p_first": round(positions[0] / n_iter, 4),
            "p_second": round(positions[1] / n_iter, 4),
            "p_third": round(positions[2] / n_iter, 4),
            "p_fourth": round(positions[3] / n_iter, 4),
            "p_auto_advance": auto_rounded,
            "p_best_third_advance": best_third_rounded,
            "p_advance": round(auto_rounded + best_third_rounded, 4),
            "avg_points": round(points_sum[team] / n_iter, 2),
        }
    return {
        "teams": teams_out,
        "iterations": n_iter,
        "tiebreak_fallbacks": fallback_rows,
    }


def simulate_group(
    teams: list[str],
    ratings: dict[str, float],
    n_iter: int = 10000,
    seed: int | None = None,
    known: GroupResults | None = None,
) -> dict:
    """Aggregate finishing-position probabilities for one group.

    Returns ``{team: {p_first, p_second, p_third, p_fourth, p_advance,
    avg_points}}`` plus ``iterations``. ``p_advance = p_first + p_second``.

    ``known`` locks already-played matches at their real scores (see
    :func:`simulate_group_once`); omit it to simulate from scratch.
    """
    if len(teams) != 4:
        raise ValueError(
            f"simulate_group expects exactly 4 teams (WC 2026 group format); got {len(teams)}."
        )
    rng = np.random.default_rng(seed)
    counts = {t: [0, 0, 0, 0] for t in teams}  # rank 1..4 tallies
    points_sum = dict.fromkeys(teams, 0)

    for _ in range(n_iter):
        standings = simulate_group_once(rng, teams, ratings, known)
        for row in standings:
            counts[row["team"]][row["rank"] - 1] += 1
            points_sum[row["team"]] += row["points"]

    out = {}
    for t in teams:
        c = counts[t]
        out[t] = {
            "p_first": round(c[0] / n_iter, 4),
            "p_second": round(c[1] / n_iter, 4),
            "p_third": round(c[2] / n_iter, 4),
            "p_fourth": round(c[3] / n_iter, 4),
            "p_advance": round((c[0] + c[1]) / n_iter, 4),
            "avg_points": round(points_sum[t] / n_iter, 2),
        }
    return {"teams": out, "iterations": n_iter}
