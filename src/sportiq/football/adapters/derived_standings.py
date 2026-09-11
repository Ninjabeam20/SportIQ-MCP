"""Keyless standings adapter — derives the WC 2026 table from fixtures-chain results.

The standings chain otherwise needs an API key (api-football / football-data.org);
with neither set it has no terminator and `football_get_standings` errors out. This
adapter computes the table from the fixtures chain (keyless openfootball / static
seed via the shared cache), so standings work with zero credentials. It is the
chain terminator: it always returns a (possibly empty) table rather than raising.

Output matches the live adapters' standings shape (see football_data_org.py).
"""
from __future__ import annotations

from sportiq.football.adapters.static_seed import load_wc2026
from sportiq.football.models.results_state import derived_standings


class DerivedStandingsAdapter:
    name = "derived_standings"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        # Route via the fixtures chain cache — never call an adapter directly.
        # No deadlock: the fixtures chain does not include derived_standings.
        from sportiq.football.chains import football_fixtures_chain

        result = await football_fixtures_chain.fetch()
        wc = load_wc2026()
        return derived_standings(
            result.value.get("fixtures", []), wc.get("groups", {}), wc.get("teams", {})
        )

    async def healthcheck(self) -> bool:
        return True
