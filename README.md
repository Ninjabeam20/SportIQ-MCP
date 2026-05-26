# sportiq-mcp

MCP server exposing AI-callable tools across IPL cricket, Formula 1, and FIFA World Cup 2026.

Three flagship intelligence tools sit on top of raw-data primitives:

- `cricket_build_dream11_team` — PuLP constraint solver picks a valid 11 under credit/role/team caps.
- `f1_predict_pit_strategy` — tyre-degradation model on OpenF1 telemetry recommends stop laps and compounds.
- `football_simulate_bracket` — Monte Carlo with Poisson xG projects World Cup qualification probabilities.

## Status

Phase 0 (spine). Only `sportiq_health` is registered. See `plan.md` for the full build plan.

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
