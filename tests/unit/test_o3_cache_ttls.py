"""O.3 — Assert FallbackChain TTLs match caching-policy.md."""

from sportiq import __version__
from sportiq.cricket.chains import (
    fixtures_chain,
    live_score_chain,
    odds_chain,
    pitch_data_chain,
    player_stats_chain,
    scorecard_chain,
    squad_chain,
    standings_chain,
)
from sportiq.f1.chains import f1_laps_chain, f1_standings_chain, f1_stints_chain
from sportiq.football.chains import (
    football_fixtures_chain,
    football_groups_chain,
    football_odds_chain,
    football_standings_chain,
)


def test_live_score_ttls():
    assert live_score_chain.fresh_ttl == 30
    assert live_score_chain.stale_ttl == 300


def test_scorecard_ttls():
    assert scorecard_chain.fresh_ttl == 30
    assert scorecard_chain.stale_ttl == 300


def test_fixtures_ttls():
    assert fixtures_chain.fresh_ttl == 21600
    assert fixtures_chain.stale_ttl == 86400


def test_standings_ttls():
    assert standings_chain.fresh_ttl == 600
    assert standings_chain.stale_ttl == 3600


def test_squad_ttls():
    assert squad_chain.fresh_ttl == 43200
    assert squad_chain.stale_ttl == 259200


def test_player_stats_ttls():
    assert player_stats_chain.fresh_ttl == 86400
    assert player_stats_chain.stale_ttl == 604800


def test_odds_ttls():
    assert odds_chain.fresh_ttl == 300
    assert odds_chain.stale_ttl == 86400


def test_f1_laps_and_stints_ttls_cover_completed_sessions():
    # Keyless OpenF1 serves completed sessions only (immutable): 24h fresh, 7d stale.
    for chain in (f1_laps_chain, f1_stints_chain):
        assert chain.fresh_ttl == 86400
        assert chain.stale_ttl == 604800


def test_wc_fixtures_ttl_is_static_after_tournament():
    # WC 2026 ended 2026-07-19: fixtures moved to the static-schedule class.
    assert football_fixtures_chain.fresh_ttl == 21600
    assert football_fixtures_chain.stale_ttl == 86400


def test_static_seed_cache_keys_include_package_version():
    year_long = [
        (football_groups_chain, {}),
        (pitch_data_chain, {"venue": "wankhede"}),
    ]
    for chain, kwargs in year_long:
        assert chain.fresh_ttl >= 31_536_000
        assert __version__ in chain.cache_key_fn(**kwargs)


def test_football_standings_ttls():
    assert football_standings_chain.fresh_ttl == 600
    assert football_standings_chain.stale_ttl == 3600


def test_football_odds_ttls():
    assert football_odds_chain.fresh_ttl == 300
    assert football_odds_chain.stale_ttl == 86400


def test_f1_standings_cache_key_includes_package_version():
    # Shape changed in opus cook7 T7.6; a 7-day stale entry must not outlive an upgrade.
    assert __version__ in f1_standings_chain.cache_key_fn(year=2026)
