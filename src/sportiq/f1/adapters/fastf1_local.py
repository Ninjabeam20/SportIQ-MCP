"""fastf1 offline fallback adapter — lazy-imported to avoid slow startup.

fastf1 is an optional dependency. If not installed, fetch() raises
RuntimeError (treated as a normal chain failure). Install via:
  uv pip install 'sportiq-mcp[f1]'

session_key → (year, round) mapping is resolved from a small registry
seeded from OpenF1 session metadata. Phase 3 ships a minimal static seed;
per-season auto-refresh is a Phase 3.1 follow-up.
"""
from __future__ import annotations

# Minimal static registry: session_key → (year, round_number)
# Extend as needed; Phase 3.1 will auto-fetch from OpenF1 /sessions.
_SESSION_REGISTRY: dict[int, tuple[int, int]] = {
    9877: (2025, 8),   # 2025 Monaco GP (placeholder — update with real round)
    9158: (2024, 6),   # 2024 Monaco GP
}


class FastF1LapsAdapter:
    name = "fastf1"
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
        fastf1.Cache.enable_cache("/tmp/fastf1_cache")
        session = fastf1.get_session(year, round_number, "R")
        session.load(laps=True, telemetry=False, weather=False, messages=False)
        driver_str = str(driver_number).zfill(2)
        laps = session.laps.pick_drivers(driver_str)
        lap_records = []
        for _, row in laps.iterrows():
            lap_records.append({
                "lap_number": int(row.get("LapNumber", 0)),
                "lap_duration": float(row["LapTime"].total_seconds())
                if hasattr(row.get("LapTime"), "total_seconds")
                else None,
                "compound": str(row.get("Compound", "")),
                "tyre_life": int(row.get("TyreLife", 0)),
                "driver_number": driver_number,
                "session_key": session_key,
            })
        return {"laps": lap_records}

    async def healthcheck(self) -> bool:
        try:
            import fastf1  # noqa: F401
        except ImportError:
            return False
        return True


class FastF1StandingsAdapter:
    name = "fastf1"
    budget = None

    async def fetch(self, year: int, **kwargs) -> dict:
        try:
            import fastf1
        except ImportError as exc:
            raise RuntimeError(
                "fastf1 is not installed. Run: uv pip install 'sportiq-mcp[f1]'"
            ) from exc

        fastf1.Cache.enable_cache("/tmp/fastf1_cache")
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        standings: list[dict] = []
        for _, event in schedule.iterrows():
            round_num = int(event.get("RoundNumber", 0))
            if round_num == 0:
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
                    standings.append({
                        "year": year,
                        "round": round_num,
                        "driver": str(row.get("FullName", "")),
                        "position": int(row.get("Position", 0)),
                        "points": float(row.get("Points", 0)),
                    })
            except Exception:
                continue
        return {"standings": standings}

    async def healthcheck(self) -> bool:
        try:
            import fastf1  # noqa: F401
        except ImportError:
            return False
        return True
