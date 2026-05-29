#!/usr/bin/env python
"""Live exercise harness — hits real upstreams ON PURPOSE. NOT a pytest.

Lives under scripts/ (never tests/) so CI never runs it. Calls each MCP tool
function once and prints a compact per-sport table:

    tool | source | is_stale | fallback_used | error_code | sample

Quota-aware: keyed tools are marked SKIPPED (no key) when their key is unset,
and F1/cricket do light dynamic discovery (sessions->driver, live->match) so
dependent tools get real ids without guessing. Run each tool once; the fresh
cache serves repeats.

Usage:
    uv run python scripts/live_check.py                 # all sports
    uv run python scripts/live_check.py --sport f1      # one sport (free)
    uv run python scripts/live_check.py --only f1_get_weather
"""
from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sportiq.config import settings


@dataclass
class Row:
    tool: str
    sport: str
    source: str = "-"
    is_stale: str = "-"
    fallback: str = "-"
    error: str = "-"
    sample: str = "-"


def _sample(data: Any) -> str:
    """One short representative field from a tool's data payload."""
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                return f"{k}=[{len(v)}]"
            if isinstance(v, (str, int, float, bool)):
                return f"{k}={v}"
        return ",".join(list(data.keys())[:3]) or "{}"
    if isinstance(data, list):
        return f"[{len(data)}]"
    return str(data)[:40]


def _row_from_envelope(name: str, sport: str, env: dict) -> Row:
    if "error" in env:
        err = env["error"]
        return Row(name, sport, error=err.get("code", "ERR"), sample=err.get("message", "")[:40])
    meta = env.get("meta", {})
    return Row(
        name,
        sport,
        source=str(meta.get("source", "?")),
        is_stale=str(meta.get("is_stale", "?")),
        fallback=str(meta.get("fallback_used", "?")),
        sample=_sample(env.get("data")),
    )


@dataclass
class Probe:
    name: str
    sport: str
    make: Callable[[dict], Awaitable[dict] | None]  # returns coroutine, or None to skip
    needs_key: str | None = None  # settings attr that must be truthy, else SKIPPED


async def _run_probe(p: Probe, ctx: dict) -> Row:
    if p.needs_key and not getattr(settings, p.needs_key, None):
        return Row(p.name, p.sport, source="SKIPPED (no key)")
    try:
        coro = p.make(ctx)
    except KeyError as e:
        return Row(p.name, p.sport, source=f"SKIPPED (no {e.args[0]})")
    if coro is None:
        return Row(p.name, p.sport, source="SKIPPED (no live data)")
    try:
        env = await coro
    except Exception as e:  # harness must never crash on one tool
        return Row(p.name, p.sport, error="RAISED", sample=f"{type(e).__name__}: {e}"[:50])
    return _row_from_envelope(p.name, p.sport, env)


# --------------------------------------------------------------------------- #
# Discovery — fetch a few live ids so dependent tools get real arguments.
# --------------------------------------------------------------------------- #
async def discover_f1(ctx: dict) -> None:
    from sportiq.f1 import tools

    env = await tools.f1_get_sessions(year=2023)
    sessions = env.get("data", {}).get("sessions", []) if "data" in env else []
    race = next((s for s in sessions if s.get("session_name") == "Race"), None) or (
        sessions[-1] if sessions else None
    )
    if race:
        ctx["session_key"] = race.get("session_key")
    if ctx.get("session_key"):
        denv = await tools.f1_get_drivers(session_key=ctx["session_key"])
        drivers = denv.get("data", {}).get("drivers", []) if "data" in denv else []
        nums = [d.get("driver_number") for d in drivers if d.get("driver_number")]
        if nums:
            ctx["driver_number"] = nums[0]
            ctx["driver_a"] = nums[0]
            ctx["driver_b"] = nums[1] if len(nums) > 1 else nums[0]


async def discover_cricket(ctx: dict) -> None:
    from sportiq.cricket import tools

    if not settings.cricapi_key:
        return
    env = await tools.cricket_get_live_matches()
    matches = env.get("data", {}).get("matches", []) if "data" in env else []
    if matches:
        m = matches[0]
        ctx["match_id"] = m.get("match_id") or m.get("id")
        ctx["series_id"] = m.get("series_id")


# --------------------------------------------------------------------------- #
# Probe registry per sport.
# --------------------------------------------------------------------------- #
def cricket_probes() -> list[Probe]:
    from sportiq.cricket import intel_tools as ci
    from sportiq.cricket import tools as ct

    return [
        Probe("cricket_get_live_matches", "cricket", lambda c: ct.cricket_get_live_matches(), "cricapi_key"),
        Probe("cricket_get_scorecard", "cricket", lambda c: ct.cricket_get_scorecard(c["match_id"]), "cricapi_key"),
        Probe("cricket_get_points_table", "cricket", lambda c: ct.cricket_get_points_table(c["series_id"]), "cricapi_key"),
        Probe("cricket_get_schedule", "cricket", lambda c: ct.cricket_get_schedule(), "cricapi_key"),
        Probe("cricket_get_squad", "cricket", lambda c: ct.cricket_get_squad(team="MI")),
        Probe("cricket_player_form_index", "cricket", lambda c: ci.cricket_player_form_index(player_id=c["player_id"]), "cricapi_key"),
        Probe("cricket_get_pitch_report", "cricket", lambda c: ci.cricket_get_pitch_report(venue="Wankhede Stadium")),
        Probe("cricket_get_live_odds", "cricket", lambda c: ct.cricket_get_live_odds(), "theodds_key"),
    ]


def f1_probes() -> list[Probe]:
    from sportiq.f1 import intel_tools as fi
    from sportiq.f1 import tools as ft

    return [
        Probe("f1_get_sessions", "f1", lambda c: ft.f1_get_sessions(year=2023)),
        Probe("f1_get_standings", "f1", lambda c: ft.f1_get_standings(year=2023)),
        Probe("f1_get_race_results", "f1", lambda c: ft.f1_get_race_results(year=2023, round=6)),
        Probe("f1_get_drivers", "f1", lambda c: ft.f1_get_drivers(session_key=c["session_key"])),
        Probe("f1_get_lap_times", "f1", lambda c: ft.f1_get_lap_times(session_key=c["session_key"], driver_number=c["driver_number"])),
        Probe("f1_get_weather", "f1", lambda c: ft.f1_get_weather(session_key=c["session_key"])),
        Probe("f1_tyre_degradation", "f1", lambda c: fi.f1_tyre_degradation(session_key=c["session_key"], driver_number=c["driver_number"], compound="SOFT")),
        Probe("f1_undercut_window", "f1", lambda c: fi.f1_undercut_window(session_key=c["session_key"], attacker_number=c["driver_a"], target_number=c["driver_b"], current_lap=20)),
        Probe("f1_head_to_head_pace", "f1", lambda c: fi.f1_head_to_head_pace(session_key=c["session_key"], driver_a=c["driver_a"], driver_b=c["driver_b"])),
        Probe("f1_weather_strategy_impact", "f1", lambda c: fi.f1_weather_strategy_impact(session_key=c["session_key"])),
        Probe("f1_predict_pit_strategy", "f1", lambda c: fi.f1_predict_pit_strategy(session_key=c["session_key"], driver_number=c["driver_number"], current_lap=15)),
    ]


def football_probes() -> list[Probe]:
    from sportiq.football import intel_tools as bi
    from sportiq.football import tools as bt

    return [
        Probe("football_get_fixtures", "football", lambda c: bt.football_get_fixtures(), "apifootball_key"),
        Probe("football_get_standings", "football", lambda c: bt.football_get_standings(), "apifootball_key"),
        Probe("football_get_top_scorers", "football", lambda c: bt.football_get_top_scorers(), "apifootball_key"),
        Probe("football_get_squad", "football", lambda c: bt.football_get_squad(team="ARG")),
        Probe("football_get_groups", "football", lambda c: bt.football_get_groups()),
        Probe("football_get_odds", "football", lambda c: bt.football_get_odds(), "theodds_key"),
        Probe("football_match_predictor", "football", lambda c: bi.football_match_predictor(home_team="ARG", away_team="BRA")),
        Probe("football_xg_model", "football", lambda c: bi.football_xg_model(home_team="ARG", away_team="BRA")),
        Probe("football_simulate_group", "football", lambda c: bi.football_simulate_group(group="A", iterations=500)),
        Probe("football_knockout_path", "football", lambda c: bi.football_knockout_path(team="FRA", iterations=500, seed=1)),
        Probe("football_simulate_bracket", "football", lambda c: bi.football_simulate_bracket(iterations=300, seed=1)),
    ]


def _print_table(rows: list[Row]) -> None:
    cols = ["tool", "source", "is_stale", "fallback", "error", "sample"]
    widths = {c: len(c) for c in cols}
    for r in rows:
        for c in cols:
            widths[c] = max(widths[c], len(str(getattr(r, "tool" if c == "tool" else c))))
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("-" * len(header))
    last_sport = None
    for r in rows:
        if r.sport != last_sport:
            print(f"# {r.sport}")
            last_sport = r.sport
        vals = [r.tool, r.source, r.is_stale, r.fallback, r.error, r.sample]
        print("  ".join(str(v).ljust(widths[c]) for v, c in zip(vals, cols, strict=True)))


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", choices=["cricket", "f1", "football", "all"], default="all")
    ap.add_argument("--only", default=None, help="run a single tool by name")
    args = ap.parse_args()

    chosen = ["cricket", "f1", "football"] if args.sport == "all" else [args.sport]
    discovery = {"cricket": discover_cricket, "f1": discover_f1}
    registries = {"cricket": cricket_probes, "f1": f1_probes, "football": football_probes}

    rows: list[Row] = []
    ctx: dict[str, Any] = {}
    for sport in chosen:
        disc = discovery.get(sport)
        if disc:
            try:
                await disc(ctx)
            except Exception as e:
                print(f"[discovery {sport} failed: {type(e).__name__}: {e}]")
        for probe in registries[sport]():
            if args.only and probe.name != args.only:
                continue
            rows.append(await _run_probe(probe, ctx))

    print()
    _print_table(rows)

    # Quota snapshot
    print("\n=== sportiq_health quota ===")
    try:
        from sportiq.core.health import get_health_report

        report = await get_health_report()
        print(json.dumps(report, indent=2, default=str))
    except Exception as e:
        print(f"[health failed: {type(e).__name__}: {e}]")

    from sportiq.core.http import close_client

    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
