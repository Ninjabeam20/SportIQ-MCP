"""Module-level FallbackChain singletons for all cricket tools.

Resolution order per chain:
  live_score   : cricapi → ndtv → cricbuzz → rapidapi → stale-cache
  scorecard    : cricapi → rapidapi → stale-cache
  fixtures     : cricapi → ndtv → rapidapi → stale-cache
  standings    : cricapi → rapidapi → stale-cache
  squad        : cricapi → static_seed
"""

from __future__ import annotations

from sportiq.core.fallback import FallbackChain
from sportiq.core.health import register_adapter_for_health

from sportiq.cricket.adapters.cricapi import (
    CricAPILiveMatchesAdapter,
    CricAPIPointsTableAdapter,
    CricAPIScheduleAdapter,
    CricAPIScorecardAdapter,
    CricAPISquadAdapter,
)
from sportiq.cricket.adapters.cricbuzz_scraper import CricbuzzLiveMatchesAdapter
from sportiq.cricket.adapters.ndtv_sports_scraper import NDTVLiveMatchesAdapter, NDTVScheduleAdapter
from sportiq.cricket.adapters.rapidapi_cricbuzz import (
    RapidAPICricbuzzLiveAdapter,
    RapidAPICricbuzzScheduleAdapter,
    RapidAPICricbuzzScorecardAdapter,
    RapidAPICricbuzzStandingsAdapter,
)
from sportiq.cricket.adapters.static_seed import StaticSeedSquadAdapter

# -- Adapter singletons -------------------------------------------------------

_cricapi_live = CricAPILiveMatchesAdapter()
_cricapi_scorecard = CricAPIScorecardAdapter()
_cricapi_schedule = CricAPIScheduleAdapter()
_cricapi_standings = CricAPIPointsTableAdapter()
_cricapi_squad = CricAPISquadAdapter()
_ndtv_live = NDTVLiveMatchesAdapter()
_ndtv_schedule = NDTVScheduleAdapter()
_cricbuzz_live = CricbuzzLiveMatchesAdapter()
_rapidapi_live = RapidAPICricbuzzLiveAdapter()
_rapidapi_scorecard = RapidAPICricbuzzScorecardAdapter()
_rapidapi_schedule = RapidAPICricbuzzScheduleAdapter()
_rapidapi_standings = RapidAPICricbuzzStandingsAdapter()
_static_squad = StaticSeedSquadAdapter()

# Register all adapters so sportiq_health() can report on them.
# register_adapter_for_health() dedupes by name, so listing multiple instances
# with the same `name` (e.g. all the cricapi-flavored adapters) is harmless.
for _a in [
    _cricapi_live, _cricapi_scorecard, _cricapi_schedule, _cricapi_standings, _cricapi_squad,
    _ndtv_live, _ndtv_schedule,
    _cricbuzz_live,
    _rapidapi_live, _rapidapi_scorecard, _rapidapi_schedule, _rapidapi_standings,
    _static_squad,
]:
    register_adapter_for_health(_a)

# -- Chain singletons ---------------------------------------------------------

live_score_chain: FallbackChain[dict] = FallbackChain(
    name="cricket:live_score",
    adapters=[_cricapi_live, _ndtv_live, _cricbuzz_live, _rapidapi_live],
    cache_key_fn=lambda **_: "sportiq:cricket:live_score:all",
    fresh_ttl=30,
    stale_ttl=300,
)

scorecard_chain: FallbackChain[dict] = FallbackChain(
    name="cricket:scorecard",
    adapters=[_cricapi_scorecard, _rapidapi_scorecard],
    cache_key_fn=lambda match_id, **_: f"sportiq:cricket:scorecard:{match_id}",
    fresh_ttl=30,
    stale_ttl=300,
)

fixtures_chain: FallbackChain[dict] = FallbackChain(
    name="cricket:fixtures",
    adapters=[_cricapi_schedule, _ndtv_schedule, _rapidapi_schedule],
    cache_key_fn=lambda series_id=None, **_: f"sportiq:cricket:fixtures:{series_id or 'all'}",
    fresh_ttl=21600,
    stale_ttl=86400,
)

standings_chain: FallbackChain[dict] = FallbackChain(
    name="cricket:standings",
    adapters=[_cricapi_standings, _rapidapi_standings],
    cache_key_fn=lambda series_id="", **_: f"sportiq:cricket:standings:{series_id}",
    fresh_ttl=600,
    stale_ttl=3600,
)

squad_chain: FallbackChain[dict] = FallbackChain(
    name="cricket:squad",
    adapters=[_cricapi_squad, _static_squad],
    cache_key_fn=lambda team=None, series_id=None, **_: (
        f"sportiq:cricket:squad:{team or 'all'}:{series_id or 'none'}"
    ),
    fresh_ttl=43200,
    stale_ttl=259200,
)
