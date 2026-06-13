"""Module-level FallbackChain singletons for all football tools.

Resolution order:
  fixtures   : api_football -> football_data_org -> openfootball -> static wc2026 (30min / 24h)
  standings  : api_football -> football_data_org (10min / 1h)
  groups     : static wc2026 terminator (effectively infinite)
  team_stats : api_football -> football_data_org (24h / 7d)
  squad      : api_football -> static seed (12h / 3d)
  scorers    : api_football -> football_data_org (24h / 7d)

Discipline (F1 audit finding #2): every fallback adapter in a chain shares the
same call signature and returns the same output shape.
"""
from __future__ import annotations

import hashlib

from sportiq.core.fallback import FallbackChain
from sportiq.core.health import register_adapter_for_health
from sportiq.football.adapters.api_football import (
    APIFootballFixturesAdapter,
    APIFootballScorersAdapter,
    APIFootballSquadAdapter,
    APIFootballStandingsAdapter,
    APIFootballTeamStatsAdapter,
)
from sportiq.football.adapters.football_data_org import (
    FootballDataOrgFixturesAdapter,
    FootballDataOrgScorersAdapter,
    FootballDataOrgStandingsAdapter,
    FootballDataOrgTeamStatsAdapter,
)
from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter
from sportiq.football.adapters.static_seed import (
    StaticSeedFixturesAdapter,
    StaticSeedGroupsAdapter,
    StaticSeedSquadAdapter,
)
from sportiq.football.adapters.theodds import TheOddsFootballAdapter

# -- Adapter singletons -------------------------------------------------------

_af_fixtures = APIFootballFixturesAdapter()
_af_standings = APIFootballStandingsAdapter()
_af_team_stats = APIFootballTeamStatsAdapter()
_af_squad = APIFootballSquadAdapter()
_af_scorers = APIFootballScorersAdapter()

_fd_fixtures = FootballDataOrgFixturesAdapter()
_fd_standings = FootballDataOrgStandingsAdapter()
_fd_team_stats = FootballDataOrgTeamStatsAdapter()
_fd_scorers = FootballDataOrgScorersAdapter()

_openfootball_fixtures = OpenFootballFixturesAdapter()
_seed_groups = StaticSeedGroupsAdapter()
_seed_fixtures = StaticSeedFixturesAdapter()
_seed_squad = StaticSeedSquadAdapter()
_theodds_football = TheOddsFootballAdapter()

# Register one healthcheck per upstream identity (deduped by name).
for _a in [_af_fixtures, _fd_fixtures, _openfootball_fixtures, _seed_groups, _theodds_football]:
    register_adapter_for_health(_a)

# -- Chain singletons ---------------------------------------------------------

football_fixtures_chain: FallbackChain[dict] = FallbackChain(
    name="football:fixtures",
    adapters=[_af_fixtures, _fd_fixtures, _openfootball_fixtures, _seed_fixtures],
    cache_key_fn=lambda **_: "sportiq:football:fixtures:wc2026",
    fresh_ttl=1800,
    stale_ttl=86400,
)

football_standings_chain: FallbackChain[dict] = FallbackChain(
    name="football:standings",
    adapters=[_af_standings, _fd_standings],
    cache_key_fn=lambda **_: "sportiq:football:standings:wc2026",
    fresh_ttl=600,
    stale_ttl=3600,
)

football_groups_chain: FallbackChain[dict] = FallbackChain(
    name="football:groups",
    adapters=[_seed_groups],
    cache_key_fn=lambda **_: "sportiq:football:groups:wc2026",
    fresh_ttl=31536000,
    stale_ttl=31536000,
)

football_team_stats_chain: FallbackChain[dict] = FallbackChain(
    name="football:team_stats",
    adapters=[_af_team_stats, _fd_team_stats],
    cache_key_fn=lambda team, **_: f"sportiq:football:team_stats:{team}",
    fresh_ttl=86400,
    stale_ttl=604800,
)

football_squad_chain: FallbackChain[dict] = FallbackChain(
    name="football:squad",
    adapters=[_af_squad, _seed_squad],
    cache_key_fn=lambda team, **_: "sportiq:football:squad:" + hashlib.blake2s(team.lower().encode(), digest_size=8).hexdigest(),
    fresh_ttl=43200,
    stale_ttl=259200,
)

football_scorers_chain: FallbackChain[dict] = FallbackChain(
    name="football:scorers",
    adapters=[_af_scorers, _fd_scorers],
    cache_key_fn=lambda **_: "sportiq:football:scorers:wc2026",
    fresh_ttl=86400,
    stale_ttl=604800,
)

# Odds are fetched sport-wide (one WC list); the tool applies any team filter,
# so the cache key carries no args. fresh=5min (live ceiling), stale=24h.
football_odds_chain: FallbackChain[dict] = FallbackChain(
    name="football:odds",
    adapters=[_theodds_football],
    cache_key_fn=lambda **_: "sportiq:football:odds:wc2026",
    fresh_ttl=300,
    stale_ttl=86400,
)
