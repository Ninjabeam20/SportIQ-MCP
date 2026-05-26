"""Module-level FallbackChain singletons for all cricket tools.

Resolution order per chain:
  live_score   : cricapi → ndtv → cricbuzz → rapidapi → stale-cache
  fixtures     : cricapi → ndtv → rapidapi → stale-cache
  standings    : cricapi → ndtv → rapidapi → stale-cache
  squad        : cricapi → cricsheet → static_seed
  player_stats : cricsheet → cricapi → stale-cache
"""

from __future__ import annotations

from sportiq.core.fallback import FallbackChain
from sportiq.core.health import register_adapter_for_health

from sportiq.cricket.adapters.cricapi import (
    CricAPILiveMatchesAdapter,
    CricAPIPointsTableAdapter,
    CricAPIScheduleAdapter,
    CricAPISquadAdapter,
)
from sportiq.cricket.adapters.cricbuzz_scraper import CricbuzzLiveMatchesAdapter
from sportiq.cricket.adapters.cricsheet import CricSheetPlayerStatsAdapter, CricSheetSquadAdapter
from sportiq.cricket.adapters.ndtv_sports_scraper import NDTVLiveMatchesAdapter, NDTVScheduleAdapter
from sportiq.cricket.adapters.rapidapi_cricbuzz import (
    RapidAPICricbuzzLiveAdapter,
    RapidAPICricbuzzScheduleAdapter,
    RapidAPICricbuzzStandingsAdapter,
)
from sportiq.cricket.adapters.static_seed import StaticSeedSquadAdapter

# -- Adapter singletons -------------------------------------------------------

_cricapi_live = CricAPILiveMatchesAdapter()
_cricapi_schedule = CricAPIScheduleAdapter()
_cricapi_standings = CricAPIPointsTableAdapter()
_cricapi_squad = CricAPISquadAdapter()
_cricsheet_squad = CricSheetSquadAdapter()
_cricsheet_stats = CricSheetPlayerStatsAdapter()
_ndtv_live = NDTVLiveMatchesAdapter()
_ndtv_schedule = NDTVScheduleAdapter()
_cricbuzz_live = CricbuzzLiveMatchesAdapter()
_rapidapi_live = RapidAPICricbuzzLiveAdapter()
_rapidapi_schedule = RapidAPICricbuzzScheduleAdapter()
_rapidapi_standings = RapidAPICricbuzzStandingsAdapter()
_static_squad = StaticSeedSquadAdapter()

# Register all adapters so sportiq_health() can report on them
for _a in [
    _cricapi_live, _ndtv_live, _cricbuzz_live, _rapidapi_live,
    _cricapi_schedule, _ndtv_schedule, _rapidapi_schedule,
    _cricapi_standings, _rapidapi_standings,
    _cricapi_squad, _cricsheet_squad, _static_squad,
    _cricsheet_stats,
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
    adapters=[_cricapi_squad, _cricsheet_squad, _static_squad],
    cache_key_fn=lambda team=None, series_id=None, **_: (
        f"sportiq:cricket:squad:{team or 'all'}:{series_id or 'none'}"
    ),
    fresh_ttl=43200,
    stale_ttl=259200,
)

player_stats_chain: FallbackChain[dict] = FallbackChain(
    name="cricket:player_stats",
    adapters=[_cricsheet_stats, _cricapi_live],
    cache_key_fn=lambda player_name="", **_: f"sportiq:cricket:player_stats:{player_name}",
    fresh_ttl=86400,
    stale_ttl=604800,
)
