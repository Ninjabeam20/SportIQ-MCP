# sportiq-mcp

MCP server exposing AI-callable tools across IPL cricket, Formula 1, and FIFA World Cup 2026.

Three flagship intelligence tools sit on top of raw-data primitives:

- `cricket_build_dream11_team` — PuLP constraint solver picks a valid 11 under credit/role/team caps.
- `f1_predict_pit_strategy` — tyre-degradation model on OpenF1 telemetry recommends stop laps and compounds.
- `football_simulate_bracket` — Monte Carlo with Poisson xG projects World Cup qualification probabilities.

## Status

Phase 2 complete — 5 cricket RAW + 5 cricket INTEL tools live, including the `cricket_build_dream11_team` PuLP ILP flagship. See `plan.md` for the full build plan and `phase2.md` for the Phase 2 implementation log.

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

| Tool | What it does |
| :--- | :--- |
| `cricket_build_dream11_team` | Optimal Dream11 XI + C/VC under T20 fantasy constraints |
| `cricket_captain_recommendation` | Top-3 captain candidates by projected points |
| `cricket_differential_picks` | Low-ownership picks with projected upside (ownership estimated) |
| `cricket_player_form_index` | 0-100 form score from career stats + (future) recent innings |
| `cricket_get_pitch_report` | Pitch friendliness + recommendation for a venue |

The Dream11 solver uses CBC via PuLP. On macOS arm64 install with `brew install cbc`; the binary bundled with PuLP is x86-only and won't run on Apple Silicon.

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
