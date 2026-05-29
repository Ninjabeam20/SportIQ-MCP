"""Module-level FallbackChain singletons for all cricket tools.

Resolution order per chain:
  live_score    : cricapi → ndtv → cricbuzz → rapidapi → stale-cache
  scorecard     : cricapi → rapidapi → stale-cache
  fixtures      : cricapi → ndtv → rapidapi → stale-cache
  standings     : cricapi → rapidapi → stale-cache
  squad         : cricapi → static_seed
  player_stats  : cricapi_player_info → rapidapi_player_stats → stale-cache
  pitch_data    : static_venue (terminator only; v1 is offline-only)
"""

from __future__ import annotations

from sportiq.core.fallback import FallbackChain
from sportiq.core.health import register_adapter_for_health
from sportiq.cricket.adapters.cricapi import (
    CricAPILiveMatchesAdapter,
    CricAPIPlayerInfoAdapter,
    CricAPIPointsTableAdapter,
    CricAPIScheduleAdapter,
    CricAPIScorecardAdapter,
    CricAPISquadAdapter,
)
from sportiq.cricket.adapters.cricbuzz_scraper import CricbuzzLiveMatchesAdapter
from sportiq.cricket.adapters.ndtv_sports_scraper import NDTVLiveMatchesAdapter, NDTVScheduleAdapter
from sportiq.cricket.adapters.rapidapi_cricbuzz import (
    RapidAPICricbuzzLiveAdapter,
    RapidAPICricbuzzPlayerStatsAdapter,
    RapidAPICricbuzzScheduleAdapter,
    RapidAPICricbuzzScorecardAdapter,
    RapidAPICricbuzzStandingsAdapter,
)
from sportiq.cricket.adapters.static_seed import (
    StaticSeedSquadAdapter,
    StaticSeedVenueAdapter,
)
from sportiq.cricket.adapters.theodds import TheOddsCricketAdapter

# -- Adapter singletons -------------------------------------------------------

_cricapi_live = CricAPILiveMatchesAdapter()
_cricapi_scorecard = CricAPIScorecardAdapter()
_cricapi_schedule = CricAPIScheduleAdapter()
_cricapi_standings = CricAPIPointsTableAdapter()
_cricapi_squad = CricAPISquadAdapter()
_cricapi_player_info = CricAPIPlayerInfoAdapter()
_ndtv_live = NDTVLiveMatchesAdapter()
_ndtv_schedule = NDTVScheduleAdapter()
_cricbuzz_live = CricbuzzLiveMatchesAdapter()
_rapidapi_live = RapidAPICricbuzzLiveAdapter()
_rapidapi_scorecard = RapidAPICricbuzzScorecardAdapter()
_rapidapi_schedule = RapidAPICricbuzzScheduleAdapter()
_rapidapi_standings = RapidAPICricbuzzStandingsAdapter()
_rapidapi_player_stats = RapidAPICricbuzzPlayerStatsAdapter()
_static_squad = StaticSeedSquadAdapter()
_static_venue = StaticSeedVenueAdapter()
_theodds_cricket = TheOddsCricketAdapter()

# Register all adapters so sportiq_health() can report on them.
# register_adapter_for_health() dedupes by name, so listing multiple instances
# with the same `name` (e.g. all the cricapi-flavored adapters) is harmless.
for _a in [
    _cricapi_live, _cricapi_scorecard, _cricapi_schedule, _cricapi_standings,
    _cricapi_squad, _cricapi_player_info,
    _ndtv_live, _ndtv_schedule,
    _cricbuzz_live,
    _rapidapi_live, _rapidapi_scorecard, _rapidapi_schedule, _rapidapi_standings,
    _rapidapi_player_stats,
    _static_squad, _static_venue,
    _theodds_cricket,
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

player_stats_chain: FallbackChain[dict] = FallbackChain(
    name="cricket:player_stats",
    adapters=[_cricapi_player_info, _rapidapi_player_stats],
    cache_key_fn=lambda player_id, **_: f"sportiq:cricket:player_stats:{player_id}",
    fresh_ttl=86400,
    stale_ttl=604800,
)

pitch_data_chain: FallbackChain[dict] = FallbackChain(
    name="cricket:pitch_data",
    adapters=[_static_venue],
    cache_key_fn=lambda venue, **_: f"sportiq:cricket:pitch:{venue.lower().replace(' ', '_')}",
    fresh_ttl=31_536_000,
    stale_ttl=0,
)

# Odds are fetched sport-wide (one IPL list); the tool applies any team filter,
# so the cache key carries no args. fresh=5min (live ceiling), stale=24h.
odds_chain: FallbackChain[dict] = FallbackChain(
    name="cricket:odds",
    adapters=[_theodds_cricket],
    cache_key_fn=lambda **_: "sportiq:cricket:odds:ipl",
    fresh_ttl=300,
    stale_ttl=86400,
)
