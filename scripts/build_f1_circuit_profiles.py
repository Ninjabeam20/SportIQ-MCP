"""Build ``f1/data/circuits.json`` — per-circuit pit-loss + stop profiles from
OpenF1 lap data + F1DB (CC BY 4.0).

Replaces the flat hardcoded ``pit_loss_s = 22.0`` / generic stop assumptions in
``f1_undercut_window`` and ``f1_predict_pit_strategy`` with measured per-circuit
numbers. Same offline-seed lineage as ``elo_seed.json``: raw data lives only in
``datasets/`` (gitignored); this derives a small committed JSON the F1 tools read.

``pit_loss_s`` semantics — time LOST by pitting vs staying out, the quantity
``models/undercut.py`` adds to the gap. Measured per stop from OpenF1 laps as

    loss = in_lap + out_lap - 2 x baseline

where ``baseline`` is the driver's clean-lap pace (median of the fastest half of
their green-flag laps — robust to SC/VSC laps). F1DB pit-stop ``timeMillis`` is
pit-lane *transit* time (entry line → exit line), NOT loss — it overestimates
loss by the bypass time and inverts orderings (Monaco transit > Spa transit but
Monaco LOSS is among the lowest), so it is deliberately not used for
``pit_loss_s``. F1DB still supplies ``typical_stops`` and ``lap_length_km``.

The seed is keyed by OpenF1 ``circuit_key`` (a stable integer that every OpenF1
session payload already carries), so the runtime resolver is an exact integer
lookup — no fuzzy circuit-name matching. The build-time F1DB→OpenF1 alias table
below is explicit and fails loud on any current-calendar circuit it cannot map.

Download F1DB once (NOT a runtime dep):

    mkdir -p datasets && cd datasets
    curl -sSL -O https://github.com/f1db/f1db/releases/latest/download/f1db-csv.zip
    mkdir -p f1db && (cd f1db && unzip -oq ../f1db-csv.zip)

Run (OpenF1 responses are cached under ``datasets/openf1/`` — re-runs are offline):

    uv run python scripts/build_f1_circuit_profiles.py

F1DB credit (CC BY 4.0 requirement) lives in the README "Data sources & credits".
"""
from __future__ import annotations

import csv
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
F1DB = ROOT / "datasets" / "f1db"
OPENF1_CACHE = ROOT / "datasets" / "openf1"
OPENF1_BASE = "https://api.openf1.org/v1"
OUT = ROOT / "src" / "sportiq" / "f1" / "data" / "circuits.json"

# Seasons that reflect the current pit-lane layouts / car spec. Older data uses
# different pit procedures and is excluded for accuracy, not for data volume.
# F1DB side (stops/lap-length) can reach back to 2022; OpenF1 starts 2023.
SEASONS = {"2022", "2023", "2024", "2025"}
OPENF1_SEASONS = (2023, 2024, 2025)
# Per-stop losses outside this band are SC/VSC-pit artefacts, penalties or
# red-flag stops — not representative green-flag pit losses.
LOSS_BAND = (8.0, 45.0)
# A circuit needs at least this many in-band loss samples to trust the median.
MIN_LOSS_SAMPLES = 20

# F1DB circuitId -> (OpenF1 circuit_key, OpenF1 circuit_short_name, country).
# Built once from the OpenF1 sessions feed; the current calendar's 24 circuits.
ALIAS: dict[str, tuple[int, str, str]] = {
    "silverstone": (2, "Silverstone", "United Kingdom"),
    "hungaroring": (4, "Hungaroring", "Hungary"),
    "imola": (6, "Imola", "Italy"),
    "spa-francorchamps": (7, "Spa-Francorchamps", "Belgium"),
    "austin": (9, "Austin", "United States"),
    "melbourne": (10, "Melbourne", "Australia"),
    "interlagos": (14, "Interlagos", "Brazil"),
    "catalunya": (15, "Catalunya", "Spain"),
    "spielberg": (19, "Spielberg", "Austria"),
    "monaco": (22, "Monte Carlo", "Monaco"),
    "montreal": (23, "Montreal", "Canada"),
    "monza": (39, "Monza", "Italy"),
    "suzuka": (46, "Suzuka", "Japan"),
    "shanghai": (49, "Shanghai", "China"),
    "zandvoort": (55, "Zandvoort", "Netherlands"),
    "marina-bay": (61, "Singapore", "Singapore"),
    "bahrain": (63, "Sakhir", "Bahrain"),
    "mexico-city": (65, "Mexico City", "Mexico"),
    "yas-marina": (70, "Yas Marina Circuit", "United Arab Emirates"),
    "baku": (144, "Baku", "Azerbaijan"),
    "jeddah": (149, "Jeddah", "Saudi Arabia"),
    "lusail": (150, "Lusail", "Qatar"),
    "miami": (151, "Miami", "United States"),
    "las-vegas": (152, "Las Vegas", "United States"),
}


def _read(name: str) -> list[dict]:
    with (F1DB / name).open() as f:
        return list(csv.DictReader(f))


_CLIENT = httpx.Client(timeout=60.0)  # shared: reuse connections, no port churn


def _openf1_get(path: str, **params) -> list[dict]:
    """Fetch an OpenF1 endpoint with a datasets/ file cache (offline re-runs)."""
    slug = path.strip("/") + "_" + "_".join(f"{k}-{v}" for k, v in sorted(params.items()))
    cache = OPENF1_CACHE / f"{slug}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    for attempt in range(8):
        try:
            resp = _CLIENT.get(f"{OPENF1_BASE}/{path.strip('/')}", params=params)
        except httpx.TransportError:  # transient connect/read hiccup — back off
            time.sleep(min(5.0 * 2**attempt, 120.0))
            continue
        if resp.status_code == 429:
            time.sleep(min(5.0 * 2**attempt, 120.0))  # OpenF1 rate-limits hard
            continue
        if resp.status_code == 404:  # some sessions have no data for an endpoint
            data = []
        elif resp.status_code in (401, 403):  # OpenF1 paywalls recent data; skip
            print(f"  WARN: OpenF1 {resp.status_code} on {path} {params} — skipped")
            data = []
        else:
            resp.raise_for_status()
            data = resp.json()
        OPENF1_CACHE.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data))
        time.sleep(2.0)  # be polite; OpenF1 is free + public
        return data
    raise SystemExit(f"FAIL: OpenF1 rate-limited 8x on {path} {params}")


def measure_pit_losses() -> dict[int, list[float]]:
    """Per-circuit green-flag pit-loss samples from OpenF1 laps.

    loss = in_lap + out_lap - 2 x baseline, baseline = median of the fastest
    half of the driver's non-pit laps (robust to SC/VSC laps).
    """
    losses: dict[int, list[float]] = defaultdict(list)
    for year in OPENF1_SEASONS:
        for sess in _openf1_get("sessions", session_name="Race", year=year):
            key, circuit = sess["session_key"], sess["circuit_key"]
            laps = _openf1_get("laps", session_key=key)
            pits = _openf1_get("pit", session_key=key)
            by_driver: dict[int, dict[int, dict]] = defaultdict(dict)
            for lap in laps:
                by_driver[lap["driver_number"]][lap["lap_number"]] = lap
            in_laps = {(p["driver_number"], p["lap_number"]) for p in pits}
            for drv, dlaps in by_driver.items():
                clean = sorted(
                    lap["lap_duration"]
                    for n, lap in dlaps.items()
                    if lap.get("lap_duration")
                    and not lap.get("is_pit_out_lap")
                    and (drv, n) not in in_laps
                )
                if len(clean) < 10:
                    continue
                baseline = statistics.median(clean[: max(len(clean) // 2, 1)])
                for drv2, n in in_laps:
                    if drv2 != drv:
                        continue
                    lap_in, lap_out = dlaps.get(n), dlaps.get(n + 1)
                    if not lap_in or not lap_out:
                        continue
                    if not lap_in.get("lap_duration") or not lap_out.get("lap_duration"):
                        continue
                    loss = lap_in["lap_duration"] + lap_out["lap_duration"] - 2 * baseline
                    if LOSS_BAND[0] <= loss <= LOSS_BAND[1]:
                        losses[circuit].append(loss)
    return losses


def build_profiles() -> dict[str, dict]:
    race_circuit = {r["id"]: r["circuitId"] for r in _read("f1db-races.csv")}
    circuit_len = {c["id"]: c["length"] for c in _read("f1db-circuits.csv")}

    # NOTE: typical_stops counts ALL recorded stops (incl. penalty/red-flag ones —
    # they are real visits to the pit lane). typical_stops and lap_length_km are
    # currently UNCONSUMED by runtime code: future-use context fields only.
    stops: dict[str, dict[tuple[str, str], int]] = defaultdict(dict)
    for p in _read("f1db-races-pit-stops.csv"):
        if p["year"] not in SEASONS:
            continue
        cid = race_circuit.get(p["raceId"])
        if cid not in ALIAS:
            continue
        key = (p["raceId"], p["driverId"])
        stops[cid][key] = max(stops[cid].get(key, 0), int(p["stop"]))

    losses = measure_pit_losses()

    profiles: dict[str, dict] = {}
    missing = []
    for cid, (ckey, short, country) in ALIAS.items():
        samples = losses.get(ckey, [])
        if len(samples) < MIN_LOSS_SAMPLES:
            missing.append(f"{cid} (n={len(samples)})")
            continue
        stop_counts = list(stops[cid].values())
        profiles[str(ckey)] = {
            "circuit": short,
            "country": country,
            "f1db_id": cid,
            "pit_loss_s": round(statistics.median(samples), 1),
            "typical_stops": round(statistics.median(stop_counts)) if stop_counts else 2,
            "lap_length_km": round(float(circuit_len.get(cid, 0.0)), 3),
            "sample_size": len(samples),
        }
    if missing:
        raise SystemExit(f"FAIL: calendar circuits with too few pit-loss samples: {missing}")
    return dict(sorted(profiles.items(), key=lambda kv: int(kv[0])))


def main() -> None:
    profiles = build_profiles()
    OUT.write_text(json.dumps(profiles, indent=2) + "\n")
    vals = [p["pit_loss_s"] for p in profiles.values()]
    print(f"Wrote {len(profiles)} circuit profiles to {OUT.relative_to(ROOT)}")
    print(f"pit_loss range [{min(vals)}, {max(vals)}]s  (flat hardcode was 22.0s)")
    for p in sorted(profiles.values(), key=lambda x: x["pit_loss_s"]):
        print(f"  {p['circuit']:<18} {p['pit_loss_s']:>5}s  ({p['sample_size']} stops)")


if __name__ == "__main__":
    main()
