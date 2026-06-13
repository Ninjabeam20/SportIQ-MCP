"""O.3 — Assert FallbackChain TTLs match caching-policy.md."""
from sportiq.cricket.chains import (
    fixtures_chain,
    live_score_chain,
    odds_chain,
    player_stats_chain,
    scorecard_chain,
    squad_chain,
    standings_chain,
)
from sportiq.f1.chains import f1_laps_chain, f1_stints_chain
from sportiq.football.chains import (
    football_fixtures_chain,
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


def test_f1_laps_ttls():
    # F1 live telemetry: fresh 10s, stale 60s
    assert f1_laps_chain.fresh_ttl == 10
    assert f1_laps_chain.stale_ttl == 60


def test_f1_stints_ttls():
    # F1 live telemetry: fresh 10s, stale 60s
    assert f1_stints_chain.fresh_ttl == 10
    assert f1_stints_chain.stale_ttl == 60


def test_football_fixtures_ttls():
    # 30min fresh: the chain now carries live WC results (openfootball + keyed
    # football-data.org), so it refreshes far sooner than a static schedule.
    assert football_fixtures_chain.fresh_ttl == 1800
    assert football_fixtures_chain.stale_ttl == 86400


def test_football_standings_ttls():
    assert football_standings_chain.fresh_ttl == 600
    assert football_standings_chain.stale_ttl == 3600


def test_football_odds_ttls():
    assert football_odds_chain.fresh_ttl == 300
    assert football_odds_chain.stale_ttl == 86400
