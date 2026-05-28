# sportiq-mcp

MCP server exposing AI-callable tools across IPL cricket, Formula 1, and FIFA World Cup 2026.

Three flagship intelligence tools sit on top of raw-data primitives:

- `cricket_build_dream11_team` — PuLP constraint solver picks a valid 11 under credit/role/team caps.
- `f1_predict_pit_strategy` — tyre-degradation model on OpenF1 telemetry recommends stop laps and compounds.
- `football_simulate_bracket` — Monte Carlo with Poisson xG projects World Cup qualification probabilities.

## Status

Phase 3 complete — 5 cricket RAW + 5 cricket INTEL + 6 F1 RAW + 5 F1 INTEL tools live (22 total). Flagships: `cricket_build_dream11_team` (PuLP ILP) and `f1_predict_pit_strategy` (tyre-degradation model). See `plan.md` for the full build plan.

## Cricket tools

### RAW (Phase 1)

| Tool | What it does |
| :--- | :--- |
| `cricket_get_live_matches` | All currently live matches across all series |
| `cricket_get_scorecard` | Full scorecard for a match by ID |
| `cricket_get_points_table` | Series standings / points table |
| `cricket_get_schedule` | Upcoming fixtures, optionally by series |
| `cricket_get_squad` | Team roster; always succeeds via static seed fallback |

### INTEL (Phase 2)

<!-- TODO: Dream11 demo GIF -->

| Tool | What it does |
| :--- | :--- |
| `cricket_build_dream11_team` | Optimal Dream11 XI + C/VC under T20 fantasy constraints |
| `cricket_captain_recommendation` | Top-3 captain candidates by projected points |
| `cricket_differential_picks` | Low-ownership picks with projected upside (ownership estimated) |
| `cricket_player_form_index` | 0-100 form score from career stats + (future) recent innings |
| `cricket_get_pitch_report` | Pitch friendliness + recommendation for a venue |

The Dream11 solver uses CBC via PuLP. On macOS arm64 install with `brew install cbc`; the binary bundled with PuLP is x86-only and won't run on Apple Silicon.

## F1 Tools

### RAW (Phase 3)

| Tool | Description |
|------|-------------|
| `f1_get_sessions` | List F1 race/qualifying/practice sessions by year |
| `f1_get_drivers` | Driver list for a session |
| `f1_get_lap_times` | Per-driver lap times with compound data |
| `f1_get_standings` | Driver + constructor championship standings |
| `f1_get_race_results` | Race results for a session |
| `f1_get_weather` | Track weather data (temp, rainfall, wind) |

### INTEL (Phase 3)

| Tool | Type | Description |
|------|------|-------------|
| `f1_tyre_degradation` | INTEL | Fit linear tyre-degradation model per compound |
| `f1_undercut_window` | INTEL | Is an undercut viable vs a target driver? |
| `f1_head_to_head_pace` | INTEL | Lap-time pace comparison between two drivers |
| `f1_weather_strategy_impact` | INTEL | Weather-based compound recommendation |
| `f1_predict_pit_strategy` | **FLAGSHIP** | Predict optimal pit stops + compound sequence |

Data sources: [OpenF1](https://openf1.org) (free, keyless) → [Jolpica](https://jolpi.ca) → `fastf1` (optional, offline, `pip install sportiq-mcp[f1]`).

### Cricket adapter defaults

By default only CricAPI (key required) and static data are active. Opt-in adapters:

```bash
SPORTIQ_ENABLE_NDTV=1         # NDTV Sports scraper (operator accepts ToS risk)
SPORTIQ_ENABLE_CRICBUZZ=1     # Cricbuzz scraper (operator accepts ToS risk)
RAPIDAPI_KEY=your_key         # Licensed Cricbuzz mirror via RapidAPI
```

Copy `.env.example` to `.env` and fill in keys.

## Install

```bash
# from PyPI (post-release)
uvx sportiq-mcp

# from source
git clone https://github.com/Ninjabeam20/sportiq-mcp
cd sportiq-mcp
uv sync
uv run python -m sportiq.server
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "sportiq": {
      "command": "uvx",
      "args": ["sportiq-mcp"]
    }
  }
}
```

## Develop

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
npx @modelcontextprotocol/inspector uv run python -m sportiq.server
```

See `CLAUDE.md` for collaboration rules and `docs/index.md` for the wiki entry point.

## License

MIT
