# sportiq-mcp

[![CI](https://github.com/Ninjabeam20/sportiq-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/Ninjabeam20/sportiq-mcp/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/sportiq-mcp.svg)](https://pypi.org/project/sportiq-mcp/)
![tools](https://img.shields.io/badge/tools-44-blue)

MCP server exposing AI-callable tools across IPL cricket, Formula 1, and FIFA World Cup 2026.

Three flagship intelligence tools sit on top of raw-data primitives:

- `cricket_build_dream11_team` — PuLP constraint solver picks a valid 11 under credit/role/team caps.
- `f1_predict_pit_strategy` — tyre-degradation model on OpenF1 telemetry recommends stop laps and compounds.
- `football_simulate_bracket` — Monte Carlo with Poisson xG projects World Cup qualification probabilities.

## Status

Phase 10 complete — **44 tools live**: 6 cricket RAW + 8 cricket INTEL + 6 F1 RAW + 7 F1 INTEL + 7 football RAW + 8 football INTEL + 1 cross-sport + `sportiq_health`. All three flagships shipped: `cricket_build_dream11_team` (PuLP ILP), `f1_predict_pit_strategy` (tyre-degradation on OpenF1 telemetry), and `football_simulate_bracket` (Monte Carlo + Poisson xG over the 48-team WC 2026 format). See `plan.md` for the full build plan.

## Cricket tools

### RAW (Phase 1)

| Tool | What it does |
| :--- | :--- |
| `cricket_get_live_matches` | All currently live matches across all series |
| `cricket_get_scorecard` | Full scorecard for a match by ID |
| `cricket_get_points_table` | Series standings / points table |
| `cricket_get_schedule` | Upcoming fixtures, optionally by series |
| `cricket_get_squad` | Team roster; always succeeds via static seed fallback |
| `cricket_get_live_odds` | Live bookmaker head-to-head odds for upcoming/live IPL matches |

### INTEL (Phase 2)

<!-- TODO: Dream11 demo GIF -->

| Tool | What it does |
| :--- | :--- |
| `cricket_build_dream11_team` | Optimal Dream11 XI + C/VC under T20 fantasy constraints |
| `cricket_captain_recommendation` | Top-3 captain candidates by projected points |
| `cricket_differential_picks` | Low-ownership picks with projected upside (ownership estimated) |
| `cricket_player_form_index` | 0-100 form score from career stats + (future) recent innings |
| `cricket_get_pitch_report` | Pitch friendliness + recommendation for a venue |
| `cricket_head_to_head` | Compare two teams head-to-head using squad form and player stats |
| `cricket_player_matchup` | Head-to-head matchup between two players by role and career stats |
| `cricket_find_value_bets` | Screen upcoming IPL odds for +EV ("value") bets (requires `THEODDS_KEY`) |

The Dream11 solver uses CBC via PuLP. On macOS arm64 install with `brew install cbc`; the binary bundled with PuLP is x86-only and won't run on Apple Silicon.

## F1 Tools

### RAW (Phase 3)

| Tool | Description |
|------|-------------|
| `f1_get_sessions` | List F1 race/qualifying/practice sessions by year |
| `f1_get_drivers` | Driver list for a session |
| `f1_get_lap_times` | Per-driver lap times (compound lives on stints, not laps) |
| `f1_get_standings` | Driver + constructor championship standings |
| `f1_get_race_results` | Final race classification by year + round (Jolpica) |
| `f1_get_weather` | Track weather data (temp, rainfall, wind) |

### INTEL (Phase 3)

| Tool | Type | Description |
|------|------|-------------|
| `f1_tyre_degradation` | INTEL | Fit linear tyre-degradation model per compound |
| `f1_undercut_window` | INTEL | Is an undercut viable vs a target driver? |
| `f1_head_to_head_pace` | INTEL | Lap-time pace comparison between two drivers |
| `f1_weather_strategy_impact` | INTEL | Weather-based compound recommendation |
| `f1_qualifying_analysis` | INTEL | Best lap per driver, gap to pole, projected grid |
| `f1_race_pace_compare` | INTEL | Race-pace + tyre-degradation comparison between two drivers |
| `f1_predict_pit_strategy` | **FLAGSHIP** | Predict optimal pit stops + compound sequence |

Data sources: [OpenF1](https://openf1.org) (free, keyless) → [Jolpica](https://jolpi.ca) → `fastf1` (optional, offline, `pip install sportiq-mcp[f1]`).

## Football tools (FIFA World Cup 2026)

### RAW (Phase 4)

| Tool | Description |
|------|-------------|
| `football_get_groups` | WC 2026 group draw (12 groups of 4) + advancement format |
| `football_get_fixtures` | Fixtures (live providers, else the group schedule) |
| `football_get_standings` | Current group standings |
| `football_get_squad` | National-team squad |
| `football_get_match_stats` | Team aggregate tournament statistics |
| `football_get_top_scorers` | Tournament top scorers |
| `football_get_odds` | Live bookmaker head-to-head odds for upcoming WC 2026 matches |

### INTEL (Phase 4)

| Tool | Type | Description |
|------|------|-------------|
| `football_xg_model` | INTEL | Expected goals + win/draw/loss probabilities (Elo-driven Poisson) |
| `football_match_predictor` | INTEL | Most likely scoreline + outcome for one match |
| `football_simulate_group` | INTEL | Monte Carlo a group into qualification probabilities |
| `football_simulate_bracket` | **FLAGSHIP** | Monte Carlo the full 48-team WC into per-team round + title probabilities |
| `football_knockout_path` | INTEL | Round-by-round survival probabilities for one team |
| `football_form_trends` | INTEL | Rolling form, goal record, and xG trend for a team |
| `football_find_value_bets` | INTEL | +EV bets where model win prob beats the market |
| `football_build_accumulator` | INTEL | Accumulator from the top value bets across live markets |

The 2026 format (48 teams, 12 groups, top 2 + 8 best thirds → 32-team knockout) is encoded in `wc2026.json`. Data sources: [API-Football](https://www.api-football.com) (`APIFOOTBALL_KEY`) → [football-data.org](https://football-data.org) (free, token optional) → bundled `wc2026.json` seed.

## Cross-sport tools

| Tool | Type | Description |
|------|------|-------------|
| `cross_sport_build_accumulator` | INTEL | Accumulator mixing football and cricket value bets |

## Diagnostics

| Tool | Description |
| :--- | :--- |
| `sportiq_health` | Cache backend + per-adapter status and remaining API quota |

### Cricket adapter defaults

By default only CricAPI (key required) and static data are active. Opt-in adapters:

```bash
SPORTIQ_ENABLE_NDTV=1         # NDTV Sports scraper (operator accepts ToS risk)
SPORTIQ_ENABLE_CRICBUZZ=1     # Cricbuzz scraper (operator accepts ToS risk)
RAPIDAPI_KEY=your_key         # Licensed Cricbuzz mirror via RapidAPI
```

Copy `.env.example` to `.env` and fill in keys.

### RapidAPI Hub MCP servers

`.mcp.json` also wires three external [RapidAPI Hub](https://rapidapi.com) MCP servers (Sportspage Feeds, Football Prediction, Live Sports Odds) via `mcp-remote`. Because `.mcp.json` is committed, the API key is a placeholder — replace each `<RAPIDAPI_KEY>` in `.mcp.json` with your real RapidAPI key locally to enable them. They run as separate MCP servers and do not affect the in-process `sportiq` tools.

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
      "args": ["sportiq-mcp"],
      "env": {
        "CRICAPI_KEY": "your_cricapi_key",
        "APIFOOTBALL_KEY": "your_apifootball_key",
        "THEODDS_KEY": "your_theodds_key"
      }
    }
  }
}
```

All env vars are optional — the server boots and serves seed/free-source data
without any keys. Add a key to unlock the source it gates (e.g. `THEODDS_KEY`
for the value-bet tools). F1 and most football tools use free, keyless sources.

**Transport:** stdio only (local subprocess), which is the right fit for a
single-client desktop integration. There is no remote/streamable-HTTP endpoint;
running it as a shared remote service is out of scope.

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
