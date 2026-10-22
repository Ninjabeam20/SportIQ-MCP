"""fastf1 offline fallback adapter — lazy-imported to avoid slow startup.

fastf1 is an optional dependency. If not installed, fetch() raises
RuntimeError (treated as a normal chain failure). Install via:
  uv pip install 'sportiq-mcp[f1]'

session_key → (year, round) mapping is resolved from a small registry
seeded from OpenF1 session metadata. Phase 3 ships a minimal static seed;
per-season auto-refresh is a Phase 3.1 follow-up.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

# Minimal static registry: session_key → (year, round_number)
# Extend as needed; Phase 3.1 will auto-fetch from OpenF1 /sessions.
_SESSION_REGISTRY: dict[int, tuple[int, int]] = {
    9877: (2025, 8),  # 2025 Monaco GP (placeholder — update with real round)
    9158: (2024, 6),  # 2024 Monaco GP
}


class FastF1LapsAdapter:
    name = "fastf1"
    optional_import = "fastf1"  # sportiq_health: missing extra is healthy
    budget = None

    async def fetch(self, session_key: int, driver_number: int, **kwargs) -> dict:
        try:
            import fastf1
        except ImportError as exc:
            raise RuntimeError(
                "fastf1 is not installed. Run: uv pip install 'sportiq-mcp[f1]'"
            ) from exc

        if session_key not in _SESSION_REGISTRY:
            raise RuntimeError(
                f"session_key={session_key} not in static registry. "
                "Add it to _SESSION_REGISTRY or use the OpenF1 adapter."
            )
        year, round_number = _SESSION_REGISTRY[session_key]

        def _load_laps() -> list[dict]:
            cache_dir = os.path.join(tempfile.gettempdir(), "fastf1_cache")
            fastf1.Cache.enable_cache(cache_dir)
            session = fastf1.get_session(year, round_number, "R")
            session.load(laps=True, telemetry=False, weather=False, messages=False)
            driver_str = str(driver_number).zfill(2)
            laps = session.laps.pick_drivers(driver_str)
            lap_records = []
            for _, row in laps.iterrows():
                lap_records.append(
                    {
                        "lap_number": int(row.get("LapNumber", 0)),
                        "lap_duration": float(row["LapTime"].total_seconds())
                        if hasattr(row.get("LapTime"), "total_seconds")
                        else None,
                        "compound": str(row.get("Compound", "")),
                        "tyre_life": int(row.get("TyreLife", 0)),
                        "driver_number": driver_number,
                        "session_key": session_key,
                    }
                )
            return lap_records

        lap_records = await asyncio.to_thread(_load_laps)
        return {"laps": lap_records}

    async def healthcheck(self) -> bool:
        try:
            import fastf1  # noqa: F401
        except ImportError:
            return False
        return True


class FastF1StandingsAdapter:
    name = "fastf1"
    optional_import = "fastf1"  # sportiq_health: missing extra is healthy
    budget = None

    async def fetch(self, year: int, **kwargs) -> dict:
        try:
            import fastf1
        except ImportError as exc:
            raise RuntimeError(
                "fastf1 is not installed. Run: uv pip install 'sportiq-mcp[f1]'"
            ) from exc

        def _load_standings() -> dict:
            cache_dir = os.path.join(tempfile.gettempdir(), "fastf1_cache")
            fastf1.Cache.enable_cache(cache_dir)
            schedule = fastf1.get_event_schedule(year, include_testing=False)
            # Season totals, summed over every loaded race (FastF1 results are
            # per-race). Sprint points are not loaded here; Jolpica is primary.
            drivers: dict[str, dict] = {}
            teams: dict[str, dict] = {}
            last_round = 0
            for _, event in schedule.iterrows():
                round_num = int(event.get("RoundNumber", 0))
                # Bound the loop: skip testing (0) and invalid/out-of-bounds round numbers
                if round_num <= 0 or round_num > 35:
                    continue
                try:
                    session = fastf1.get_session(year, round_num, "R")
                    session.load(
                        laps=False,
                        telemetry=False,
                        weather=False,
                        messages=False,
                        timing_data=False,
                    )
                    results = session.results
                    for _, row in results.iterrows():
                        name = str(row.get("FullName", ""))
                        team = str(row.get("TeamName", "") or "")
                        points = float(row.get("Points", 0) or 0)
                        won = int(row.get("Position", 0) or 0) == 1
                        number = row.get("DriverNumber")
                        entry = drivers.setdefault(
                            name,
                            {
                                "driver_number": int(number) if str(number).isdigit() else None,
                                "code": str(row.get("Abbreviation", "") or name[:3].upper()),
                                "name": name,
                                "team": team,
                                "points": 0.0,
                                "wins": 0,
                            },
                        )
                        entry["points"] += points
                        entry["wins"] += int(won)
                        if team:
                            entry["team"] = team
                            t = teams.setdefault(team, {"team": team, "points": 0.0, "wins": 0})
                            t["points"] += points
                            t["wins"] += int(won)
                    last_round = max(last_round, round_num)
                except Exception:
                    continue

            def _ranked(rows: list[dict]) -> list[dict]:
                rows = sorted(rows, key=lambda r: (-r["points"], -r["wins"]))
                return [{"position": i, **r} for i, r in enumerate(rows, start=1)]

            return {
                "season": year,
                "round": last_round,
                "drivers": _ranked(list(drivers.values())),
                "constructors": _ranked(list(teams.values())),
            }

        return await asyncio.to_thread(_load_standings)

    async def healthcheck(self) -> bool:
        try:
            import fastf1  # noqa: F401
        except ImportError:
            return False
        return True
