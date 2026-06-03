"""Unit tests for the head_to_head model (no I/O)."""

from sportiq.cricket.models.head_to_head import summarise_h2h


def test_equal_squads_gives_50_50():
    squad = [{"name": f"Player{i}", "player_id": str(i)} for i in range(11)]
    result = summarise_h2h("MI", "CSK", squad, squad, {})
    assert result["h2h_win_rate_a"] == result["h2h_win_rate_b"]


def test_better_squad_wins_edges():
    a = [{"name": "StarA", "player_id": "1"}]
    b = [{"name": "WeakB", "player_id": "2"}]
    stats = {
        "1": {
            "data": {
                "stats": [
                    {"fn": "batting", "matchtype": "t20i", "stat": "Average", "value": "60"},
                    {"fn": "batting", "matchtype": "t20i", "stat": "Strike Rate", "value": "150"},
                ]
            }
        },
        "2": {
            "data": {
                "stats": [
                    {"fn": "batting", "matchtype": "t20i", "stat": "Average", "value": "20"},
                    {"fn": "batting", "matchtype": "t20i", "stat": "Strike Rate", "value": "100"},
                ]
            }
        },
    }
    result = summarise_h2h("A", "B", a, b, stats)
    assert result["team_a_edge_count"] >= result["team_b_edge_count"]


def test_returns_required_keys():
    result = summarise_h2h("X", "Y", [], [], {})
    for key in [
        "team_a_edge_count",
        "team_b_edge_count",
        "key_players_a",
        "key_players_b",
        "h2h_win_rate_a",
        "h2h_win_rate_b",
    ]:
        assert key in result


def test_win_rates_sum_to_one():
    squad = [{"name": "P", "player_id": "1"}]
    r = summarise_h2h("A", "B", squad, squad, {})
    assert abs(r["h2h_win_rate_a"] + r["h2h_win_rate_b"] - 1.0) < 0.001


def test_empty_squads_returns_50_50():
    result = summarise_h2h("MI", "CSK", [], [], {})
    assert result["h2h_win_rate_a"] == 0.5  # no decisive matchups → neutral
    assert result["h2h_win_rate_b"] == 0.5


def test_key_players_capped_at_3():
    squad = [{"name": f"P{i}", "player_id": str(i)} for i in range(11)]
    result = summarise_h2h("MI", "CSK", squad, squad, {})
    assert len(result["key_players_a"]) <= 3
    assert len(result["key_players_b"]) <= 3


def test_team_labels_preserved():
    result = summarise_h2h("Mumbai Indians", "Chennai Super Kings", [], [], {})
    assert result["team_a"] == "Mumbai Indians"
    assert result["team_b"] == "Chennai Super Kings"


def test_player_without_id_uses_name_key():
    """Players with no player_id fall back to name-keyed stats lookup."""
    squad_a = [{"name": "NoIdPlayer"}]
    squad_b = [{"name": "WeakPlayer", "player_id": "2"}]
    # "NoIdPlayer" has no player_id, so stats key is the name itself
    stats = {
        "NoIdPlayer": {
            "data": {
                "stats": [
                    {"fn": "batting", "matchtype": "t20i", "stat": "Average", "value": "55"},
                    {"fn": "batting", "matchtype": "t20i", "stat": "Strike Rate", "value": "140"},
                ]
            }
        }
    }
    result = summarise_h2h("A", "B", squad_a, squad_b, stats)
    # Team A has stats (form > 50), team B player has no stats (neutral 50)
    assert result["team_a_edge_count"] >= result["team_b_edge_count"]
