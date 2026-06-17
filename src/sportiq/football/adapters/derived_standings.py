"""Keyless standings adapter — derives the WC 2026 table from openfootball results.

The standings chain otherwise needs an API key (api-football / football-data.org);
with neither set it has no terminator and `football_get_standings` errors out. This
adapter computes the table from the keyless, public-domain openfootball fixtures
(the same source the fixtures chain already trusts), so standings work with zero
credentials. It is the chain terminator: it always returns a (possibly empty)
table rather than raising.

Output matches the live adapters' standings shape (see football_data_org.py).
"""
from __future__ import annotations

from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter
from sportiq.football.adapters.static_seed import load_wc2026
from sportiq.football.models.results_state import derived_standings


class DerivedStandingsAdapter:
    name = "derived_standings"
    budget = None

    def __init__(self) -> None:
        self._fixtures = OpenFootballFixturesAdapter()

    async def fetch(self, **kwargs) -> dict:
        payload = await self._fixtures.fetch()
        wc = load_wc2026()
        return derived_standings(
            payload.get("fixtures", []), wc.get("groups", {}), wc.get("teams", {})
        )

    async def healthcheck(self) -> bool:
        return True
