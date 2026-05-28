"""Module-level FallbackChain singletons for all F1 tools.

Resolution order:
  sessions  : openf1 → jolpica (round-level coverage)
  laps      : openf1 → fastf1
  stints    : openf1 (only source)
  weather   : openf1 (only source)
  standings : jolpica → fastf1
  drivers   : openf1 (only source)
"""
from __future__ import annotations

from sportiq.core.fallback import FallbackChain
from sportiq.core.health import register_adapter_for_health
from sportiq.f1.adapters.fastf1_local import FastF1LapsAdapter, FastF1StandingsAdapter
from sportiq.f1.adapters.jolpica import JolpicaResultsAdapter, JolpicaStandingsAdapter
from sportiq.f1.adapters.openf1 import (
    OpenF1DriversAdapter,
    OpenF1LapsAdapter,
    OpenF1SessionsAdapter,
    OpenF1StintsAdapter,
    OpenF1WeatherAdapter,
)

# -- Adapter singletons -------------------------------------------------------

_openf1_sessions = OpenF1SessionsAdapter()
_openf1_drivers = OpenF1DriversAdapter()
_openf1_laps = OpenF1LapsAdapter()
_openf1_stints = OpenF1StintsAdapter()
_openf1_weather = OpenF1WeatherAdapter()
_jolpica_standings = JolpicaStandingsAdapter()
_jolpica_results = JolpicaResultsAdapter()
_fastf1_laps = FastF1LapsAdapter()
_fastf1_standings = FastF1StandingsAdapter()

# Register adapters. Deduped by name — openf1, jolpica, fastf1 each show once.
for _a in [
    _openf1_sessions,
    _jolpica_standings,
    _fastf1_laps,
]:
    register_adapter_for_health(_a)

# -- Chain singletons ---------------------------------------------------------

f1_sessions_chain: FallbackChain[dict] = FallbackChain(
    name="f1:sessions",
    adapters=[_openf1_sessions, _jolpica_results],
    cache_key_fn=lambda year, country=None, **_: f"sportiq:f1:sessions:{year}:{country or 'all'}",
    fresh_ttl=21600,
    stale_ttl=86400,
)

f1_laps_chain: FallbackChain[dict] = FallbackChain(
    name="f1:laps",
    adapters=[_openf1_laps, _fastf1_laps],
    cache_key_fn=lambda session_key, driver_number, **_: f"sportiq:f1:laps:{session_key}:{driver_number}",
    fresh_ttl=3600,
    stale_ttl=86400,
)

f1_stints_chain: FallbackChain[dict] = FallbackChain(
    name="f1:stints",
    adapters=[_openf1_stints],
    cache_key_fn=lambda session_key, driver_number, **_: f"sportiq:f1:stints:{session_key}:{driver_number}",
    fresh_ttl=3600,
    stale_ttl=86400,
)

f1_weather_chain: FallbackChain[dict] = FallbackChain(
    name="f1:weather",
    adapters=[_openf1_weather],
    cache_key_fn=lambda session_key, **_: f"sportiq:f1:weather:{session_key}",
    fresh_ttl=600,
    stale_ttl=86400,
)

f1_standings_chain: FallbackChain[dict] = FallbackChain(
    name="f1:standings",
    adapters=[_jolpica_standings, _fastf1_standings],
    cache_key_fn=lambda year, **_: f"sportiq:f1:standings:{year}",
    fresh_ttl=86400,
    stale_ttl=604800,
)

f1_drivers_chain: FallbackChain[dict] = FallbackChain(
    name="f1:drivers",
    adapters=[_openf1_drivers],
    cache_key_fn=lambda session_key, **_: f"sportiq:f1:drivers:{session_key}",
    fresh_ttl=86400,
    stale_ttl=604800,
)
