"""Cricket team resolver — codes and official names, no substring matching."""

from sportiq.cricket.adapters._normalize import normalise_squad_payload
from sportiq.cricket.teams import IPL_TEAM_NAMES, resolve_team_code, team_display_name


def test_resolve_team_code_accepts_lowercase_code():
    assert resolve_team_code("mi", IPL_TEAM_NAMES) == "MI"


def test_resolve_team_code_accepts_full_name():
    assert resolve_team_code("Mumbai Indians", IPL_TEAM_NAMES) == "MI"


def test_resolve_team_code_accepts_former_rcb_name():
    assert resolve_team_code("Royal Challengers Bangalore", IPL_TEAM_NAMES) == "RCB"


def test_resolve_team_code_rejects_partial_name():
    assert resolve_team_code("Kings", IPL_TEAM_NAMES) is None


def test_resolve_team_code_rejects_unknown_code():
    assert resolve_team_code("XYZ", IPL_TEAM_NAMES) is None


def test_resolve_team_code_accepts_non_ipl_seed_key_when_known():
    assert resolve_team_code("ind", ["MI", "IND"]) == "IND"
    assert resolve_team_code("IND", IPL_TEAM_NAMES) is None


def test_team_display_name_returns_official_name():
    assert team_display_name("pbks") == "Punjab Kings"
    assert team_display_name("IND") == "IND"


def _two_kings_payload() -> dict:
    return {
        "data": [
            {"teamName": "Punjab Kings", "players": [{"name": "P1", "role": "Batsman"}]},
            {"teamName": "Chennai Super Kings", "players": [{"name": "C1", "role": "Bowler"}]},
        ]
    }


def test_normalize_squad_filters_by_exact_team():
    pbks = normalise_squad_payload(_two_kings_payload(), source="cricapi", team="PBKS")
    assert [p["name"] for p in pbks["players"]] == ["P1"]
    kings = normalise_squad_payload(_two_kings_payload(), source="cricapi", team="Kings")
    assert kings["players"] == []
