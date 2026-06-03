"""Head-to-head summary from squad and player-stats data.

Compares the two squads on form, counts key-player "edges", and derives an
overall win-rate estimate from those edges. All inputs are already-fetched
upstream payloads — no network calls.
"""
from __future__ import annotations


def summarise_h2h(
    team_a: str,
    team_b: str,
    squad_a: list[dict],
    squad_b: list[dict],
    stats_by_player: dict[str, dict],
) -> dict:
    """Derive a head-to-head summary from squads + player stats.

    Args:
        team_a: team code / name (for labelling only).
        team_b: team code / name.
        squad_a: list of player dicts (each has at least "name" and optionally
            "player_id").
        squad_b: same for team_b.
        stats_by_player: {player_id: raw_stats_dict} for any players we could
            fetch. Players not present in this dict receive a neutral
            form_score=50.

    Returns:
        {
          team_a: str,
          team_b: str,
          team_a_edge_count: int,   # players from team_a with higher form
          team_b_edge_count: int,
          key_players_a: list[{name, form_score}],   # top-3 by form
          key_players_b: list[{name, form_score}],
          h2h_win_rate_a: float,   # estimated from edge ratio (0.0-1.0)
          h2h_win_rate_b: float,
        }
    """
    from sportiq.cricket.models.form_index import player_form_index

    def _score_squad(squad: list[dict]) -> list[dict]:
        scored = []
        for p in squad:
            pid = p.get("player_id") or p.get("id") or p.get("name", "")
            raw = stats_by_player.get(str(pid), {})
            fi = player_form_index(raw) if raw else {"form_score": 50, "trend": "stable"}
            scored.append({"name": p.get("name", pid), "form_score": fi["form_score"]})
        return sorted(scored, key=lambda x: x["form_score"], reverse=True)

    scored_a = _score_squad(squad_a)
    scored_b = _score_squad(squad_b)

    # Edge: each player from team_a vs the corresponding ranked player from team_b
    edges_a = edges_b = 0
    for pa, pb in zip(scored_a, scored_b, strict=False):
        if pa["form_score"] > pb["form_score"]:
            edges_a += 1
        elif pb["form_score"] > pa["form_score"]:
            edges_b += 1

    total_edges = edges_a + edges_b
    if total_edges == 0:
        # No decisive matchups (all ties or empty squads) → neutral 50/50
        h2h_a = 0.5
        h2h_b = 0.5
    else:
        h2h_a = round(edges_a / total_edges, 4)
        h2h_b = round(edges_b / total_edges, 4)

    return {
        "team_a": team_a,
        "team_b": team_b,
        "team_a_edge_count": edges_a,
        "team_b_edge_count": edges_b,
        "key_players_a": scored_a[:3],
        "key_players_b": scored_b[:3],
        "h2h_win_rate_a": h2h_a,
        "h2h_win_rate_b": h2h_b,
    }
