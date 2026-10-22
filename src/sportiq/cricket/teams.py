"""Cricket team-code resolution (codes and official franchise names).

Lets tools accept either a seed code (``"MI"``) or an official name
(``"Mumbai Indians"``) without substring matching — ``"Kings"`` must not
match both PBKS and CSK.
"""

from __future__ import annotations

from collections.abc import Iterable

# Label table only (code → official franchise name), not player data.
IPL_TEAM_NAMES: dict[str, str] = {
    "MI": "Mumbai Indians",
    "CSK": "Chennai Super Kings",
    "RCB": "Royal Challengers Bengaluru",
    "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad",
    "RR": "Rajasthan Royals",
    "DC": "Delhi Capitals",
    "PBKS": "Punjab Kings",
    "LSG": "Lucknow Super Giants",
    "GT": "Gujarat Titans",
}

# Former official names still sent by some providers.
_FORMER_NAMES: dict[str, str] = {
    "Royal Challengers Bangalore": "RCB",
}

_NAME_TO_CODE: dict[str, str] = {
    **{name.lower(): code for code, name in IPL_TEAM_NAMES.items()},
    **{name.lower(): code for name, code in _FORMER_NAMES.items()},
}


def resolve_team_code(value: str, known_codes: Iterable[str]) -> str | None:
    """Return the team code for *value* (a code or an exact official name), else None.

    Case-insensitive. A code must be in *known_codes*; a full name resolves to
    its IPL code. No substring matching.
    """
    if not value:
        return None
    wanted = value.strip()
    if wanted.upper() in {str(c).upper() for c in known_codes}:
        return wanted.upper()
    return _NAME_TO_CODE.get(wanted.lower())


def team_display_name(code: str) -> str:
    """Official franchise name for an IPL code, else the code itself."""
    return IPL_TEAM_NAMES.get(code.upper(), code)
