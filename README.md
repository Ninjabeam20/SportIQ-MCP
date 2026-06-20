# sportiq-mcp

<!-- mcp-name: io.github.Ninjabeam20/sportiq-mcp -->

[![CI](https://github.com/Ninjabeam20/SportIQ-MCP/actions/workflows/test.yml/badge.svg)](https://github.com/Ninjabeam20/SportIQ-MCP/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/sportiq-mcp.svg)](https://pypi.org/project/sportiq-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/sportiq-mcp.svg)](https://pypi.org/project/sportiq-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP Registry](https://img.shields.io/badge/MCP%20Registry-listed-blue)](https://registry.modelcontextprotocol.io)
[![tools](https://img.shields.io/badge/tools-44-blue)](#status)
[![live demo](https://img.shields.io/badge/▶_live_demo-Claude_%26_ChatGPT-orange)](#use-the-hosted-sportiq--no-install--works-on-claudeai-web--chatgpt)
<!-- POST-PUBLISH: add directory badges once listed — glama.ai and smithery.ai provide embed badges:
[![glama](GLAMA_BADGE_URL)](GLAMA_SERVER_URL) [![smithery](SMITHERY_BADGE_URL)](SMITHERY_SERVER_URL) -->

MCP server exposing AI-callable tools across FIFA World Cup 2026 football, Formula 1, and IPL cricket.

![SportIQ demo — Claude calling football_simulate_bracket for World Cup 2026 title probabilities](docs/assets/demo.gif)

*SportIQ running live in Claude and ChatGPT — Monte Carlo World Cup bracket, F1 pit strategy, and lineup optimisation, each backed by a visible MCP tool call. ([full 1-min demo](docs/assets/SportIQ.mp4))*

Three flagship intelligence tools sit on top of raw-data primitives:

- `football_simulate_bracket` — Monte Carlo with Poisson xG projects World Cup qualification probabilities.
- `f1_predict_pit_strategy` — tyre-degradation model on OpenF1 telemetry recommends stop laps and compounds.
- `cricket_build_dream11_team` — PuLP constraint solver picks a valid 11 under credit/role/team caps.

> **Try it now, no install:** a public instance is live on Cloud Run. Add
> `https://sportiq-mcp-329580761892.us-central1.run.app/mcp` as a custom connector in
> claude.ai or ChatGPT — see [Use the hosted SportIQ](#use-the-hosted-sportiq--no-install--works-on-claudeai-web--chatgpt).
> Open source, read-only, no data collection — [why it's safe](#is-it-safe-to-use).

## Status

**44 tools live**: 7 football RAW + 8 football INTEL + 6 F1 RAW + 7 F1 INTEL + 6 cricket RAW + 8 cricket INTEL + 1 cross-sport + `sportiq_health`. All three flagships shipped: `football_simulate_bracket` (Monte Carlo + Poisson xG over the 48-team WC 2026 format), `f1_predict_pit_strategy` (tyre-degradation on OpenF1 telemetry), and `cricket_build_dream11_team` (PuLP ILP).

## Football tools (FIFA World Cup 2026)

### RAW

| Tool | Description |
|------|-------------|
| `football_get_groups` | WC 2026 group draw (12 groups of 4) + advancement format |
| `football_get_fixtures` | Fixtures (live providers, else the group schedule) |
| `football_get_standings` | Current group standings |
| `football_get_squad` | National-team squad |
| `football_get_match_stats` | Team aggregate tournament statistics |
| `football_get_top_scorers` | Tournament top scorers |
| `football_get_odds` | Live market head-to-head odds for upcoming WC 2026 matches |

### INTEL

| Tool | Type | Description |
|------|------|-------------|
| `football_xg_model` | INTEL | Expected goals + win/draw/loss probabilities (Elo-driven Poisson) |
| `football_match_predictor` | INTEL | Most likely scoreline + outcome for one match |
| `football_simulate_group` | INTEL | Monte Carlo a group into qualification probabilities |
| `football_simulate_bracket` | **FLAGSHIP** | Monte Carlo the full 48-team WC into per-team round + title probabilities |
| `football_knockout_path` | INTEL | Round-by-round survival probabilities for one team |
| `football_form_trends` | INTEL | Rolling form, goal record, and xG trend for a team |
| `football_find_value_bets` | INTEL | Largest gaps between model win probability and market-implied probability |
| `football_build_accumulator` | INTEL | Joint probability of several match outcomes under the model |

The 2026 format (48 teams, 12 groups, top 2 + 8 best thirds → 32-team knockout) is encoded in `wc2026.json`. Data sources: [API-Football](https://www.api-football.com) (`APIFOOTBALL_KEY`) → [football-data.org](https://football-data.org) (free, token optional) → bundled `wc2026.json` seed.

## F1 Tools

### RAW

| Tool | Description |
|------|-------------|
| `f1_get_sessions` | List F1 race/qualifying/practice sessions by year |
| `f1_get_drivers` | Driver list for a session |
| `f1_get_lap_times` | Per-driver lap times (compound lives on stints, not laps) |
| `f1_get_standings` | Driver + constructor championship standings |
| `f1_get_race_results` | Final race classification by year + round (Jolpica) |
| `f1_get_weather` | Track weather data (temp, rainfall, wind) |

### INTEL

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

## Cricket tools

### RAW

| Tool | What it does |
| :--- | :--- |
| `cricket_get_live_matches` | All currently live matches across all series |
| `cricket_get_scorecard` | Full scorecard for a match by ID |
| `cricket_get_points_table` | Series standings / points table |
| `cricket_get_schedule` | Upcoming fixtures, optionally by series |
| `cricket_get_squad` | Team roster; always succeeds via static seed fallback |
| `cricket_get_live_odds` | Live market head-to-head odds for upcoming/live IPL matches |

### INTEL

| Tool | What it does |
| :--- | :--- |
| `cricket_build_dream11_team` | Optimal fantasy XI + C/VC under T20 role/credit constraints |
| `cricket_captain_recommendation` | Top-3 captain candidates by projected points |
| `cricket_differential_picks` | Low-ownership picks with projected upside (ownership estimated) |
| `cricket_player_form_index` | 0-100 form score from career stats + (future) recent innings |
| `cricket_get_pitch_report` | Pitch friendliness + recommendation for a venue |
| `cricket_head_to_head` | Compare two teams head-to-head using squad form and player stats |
| `cricket_player_matchup` | Head-to-head matchup between two players by role and career stats |
| `cricket_find_value_bets` | Compare model probabilities against market-implied IPL odds (requires `THEODDS_KEY`) |

The lineup solver uses CBC via PuLP. On macOS arm64 install with `brew install cbc`; the binary bundled with PuLP is x86-only and won't run on Apple Silicon.

## Cross-sport tools

| Tool | Type | Description |
|------|------|-------------|
| `cross_sport_build_accumulator` | INTEL | Joint multi-match model across football and cricket |

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

## SportIQ Pro

The raw-data tools and `sportiq_health` are free and need no key. The **intelligence
tools** — everything in the INTEL sections above, including the three flagships — require
a **SportIQ Pro** key.

Get one by sponsoring the project at **[github.com/sponsors/Ninjabeam20](https://github.com/sponsors/Ninjabeam20)**
— $10/mo, or a one-time $49 for lifetime access (first 50 backers). **Your sponsorship
welcome email contains two things: your Pro key and your personal connector link.** Which
one you use depends on how you run SportIQ:

| How you run SportIQ | What to enter | Where |
| :--- | :--- | :--- |
| **PyPI / `uvx` / Claude Desktop config / IDEs** (local install) | Enter your **key** normally as the `SPORTIQ_PRO_KEY` env var | [Claude Desktop config](#claude-desktop-config) |
| **claude.ai (web), ChatGPT, or Claude Desktop** (no install) | Add your **personal connector link** as a custom connector | [Use the hosted SportIQ](#use-the-hosted-sportiq--no-install--works-on-claudeai-web--chatgpt) |

> **Important — to use Pro in Claude or ChatGPT you must add the connector link from your
> welcome email.** It looks like
> `https://sportiq-mcp-329580761892.us-central1.run.app/u/<your-key>/mcp` (your key is built
> into the link). Add it as a custom connector with **No authentication** — there is no
> separate "enter your key" box in claude.ai or ChatGPT, so the key travels inside the link.
> The plain `…/mcp` URL (without your key) only exposes the free tools.

## Install

```bash
# from PyPI
uvx sportiq-mcp

# from source
git clone https://github.com/Ninjabeam20/SportIQ-MCP
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
        "SPORTIQ_PRO_KEY": "sq_your_pro_key",
        "CRICAPI_KEY": "your_cricapi_key",
        "APIFOOTBALL_KEY": "your_apifootball_key",
        "THEODDS_KEY": "your_theodds_key"
      }
    }
  }
}
```

All env vars are optional — the server boots and serves seed/free-source data
without any keys. Add `SPORTIQ_PRO_KEY` (from a [sponsorship](https://github.com/sponsors/Ninjabeam20))
to unlock the intelligence tools, or a data-source key to unlock the source it gates
(e.g. `THEODDS_KEY`). F1 and most football tools use free, keyless sources.

## Use the hosted SportIQ (no install — works on claude.ai web & ChatGPT)

A public instance is already running on Google Cloud Run. Add this URL as a custom
connector and SportIQ shows up in your AI's tool list — nothing to install:

```
https://sportiq-mcp-329580761892.us-central1.run.app/mcp
```

The hosted instance runs **without any API keys**, so the free tools work out of the box:
standings, schedules, squads, fixtures, and the data tools — plus the **World Cup 2026 bracket
simulation** (`football_simulate_bracket`, the 10,000-iteration Monte Carlo) is open here as a
free showcase. Live-score and live-odds tools (which need rate-limited paid keys) are off on
the shared instance — self-host with your own keys if you need those (see below).

**To unlock the rest of the Pro intelligence tools here** (group simulations, knockout paths,
match predictions, F1 strategy & tyre models, lineup optimisation), add the **personal
connector link from your [sponsorship](https://github.com/sponsors/Ninjabeam20) welcome email**
instead of the plain URL — same steps below, but paste your `…/u/<your-key>/mcp` link. Run the
free bracket sim first to see what the models do.

### Add to Claude (easiest)

1. **claude.ai (web):** Settings → **Connectors** → **Add custom connector**.
2. Name it `SportIQ` and paste the URL. For free tools, paste the plain `…/mcp` URL above; for
   **Pro**, paste your **personal `…/u/<your-key>/mcp` link from your welcome email** and pick
   **No authentication**. Save — the tools appear immediately.
3. **Claude Desktop:** same path (Settings → Connectors → Add custom connector), or use the
   `uvx` config below to run it locally with your key as `SPORTIQ_PRO_KEY`.

### Add to ChatGPT

ChatGPT needs Developer Mode turned on first:

1. **Settings → Apps & Connectors → Advanced settings → enable Developer mode.**
2. In **Settings**, make sure **"use connected apps"** (the connectors/tools toggle) is enabled
   so the model is allowed to call them.
3. Back in **Apps & Connectors → Create / Add app (MCP)** → paste the URL, give it the name
   `SportIQ`, select **No authentication**, and connect. For free tools use the plain `…/mcp`
   URL above; for **Pro**, paste your **personal `…/u/<your-key>/mcp` link from your welcome
   email** (the key rides inside the link — ChatGPT has no separate key field).
4. Once it shows **Connected**, start a chat and ask something like *"Use SportIQ to simulate
   the World Cup 2026 bracket"* — ChatGPT will call the tools.

> First request after an idle period takes ~5–10s (the server scales to zero when unused, so
> it has to wake up). After that it's fast.

## Is it safe to use?

Yes — and here's exactly why, so you can verify rather than take our word for it:

- **Completely open source, MIT licensed.** Every line is on [GitHub](https://github.com/Ninjabeam20/SportIQ-MCP)
  and the package is published on [PyPI](https://pypi.org/project/sportiq-mcp/) with signed
  build attestations. Read the code before you connect it.
- **Independently reviewed by AI code-audit agents** before launch — a full MCP-rubric audit
  (verdict: ship-ready, no security findings, no secret leak) plus a multi-agent secret/code
  sweep (verdict: clean). The findings are written up in [`SECURITY.md`](SECURITY.md#independent-review)
  so you can check them — and re-run your own audit, since the whole codebase is public.
- **Read-only.** The tools only *fetch and analyse* public sports data. There are no write,
  delete, payment, email, or file-system tools — nothing that can change anything on your side.
- **No data collection.** SportIQ doesn't ask for, store, or transmit your personal data,
  prompts, or account info. It answers a tool call and forgets it.
- **The hosted instance holds no secrets.** It runs with zero API keys, so there's nothing for
  anyone to steal and no quota of yours to burn.
- **Hardened.** Upstream content is treated as data (never instructions), API keys are redacted
  from all logs, payloads are size-capped, and scrapers are opt-in only. See
  [`SECURITY.md`](SECURITY.md) for the full trust model.

**Is the data fresh?** Yes. Live sources are polled continuously and cached with tight
freshness windows — live scores refresh every ~30s, F1 telemetry every ~10s, standings every
~10min, fixtures every ~6h. Every response carries a `meta.is_stale` flag and a data age, so
the AI tells you exactly how fresh each answer is (e.g. *"as of about 4 minutes ago…"*) instead
of guessing. Caching protects free-tier quotas — it never serves you knowingly outdated data
without flagging it.

## Self-host (your own instance, with live keys)

Prefer to run your own? Set `SPORTIQ_TRANSPORT=http` and the server serves the MCP endpoint at
`/mcp` (binds `0.0.0.0:$PORT`). A ready-to-build `Dockerfile` is included. See
**[`cloud.md`](cloud.md)** for a step-by-step Google Cloud Run deploy (free tier), then add your
own `https://…/mcp` URL as a connector. With your own keys set as env vars, the live-score and
odds tools come online too.

### Environment variables

| Var | Unlocks | Free tier |
|-----|---------|-----------|
| `SPORTIQ_PRO_KEY` | The 24 SportIQ Pro intelligence tools — [sponsor to get a key](https://github.com/sponsors/Ninjabeam20) | — |
| `APIFOOTBALL_KEY` | Live football fixtures / standings / squads / scorers | 100 req/day |
| `THEODDS_KEY` | Market odds (football + cricket probability tools) | 500 req/month |
| `FOOTBALLDATA_KEY` | football-data.org fallback (token optional) | 10 req/min |
| `CRICAPI_KEY` | Live cricket scores / scorecards / schedules / squads | 100 req/day |
| `RAPIDAPI_KEY` | Paid Cricbuzz fallback (player career stats) | plan-dependent |
| `SPORTIQ_ENABLE_NDTV` / `SPORTIQ_ENABLE_CRICBUZZ` | Opt-in cricket scrapers (off by default — ToS) | — |
| `REDIS_URL` | Shared cache backend (defaults to local diskcache) | — |
| `SPORTIQ_LOG_LEVEL` / `SPORTIQ_LOG_FORMAT` | Log verbosity / `pretty`\|`json` output | — |
| `SPORTIQ_TRANSPORT` | `stdio` (default, local) or `http` (remote/Cloud Run) | — |

**Transport:** `stdio` by default (local subprocess — the right fit for Claude Desktop, Cursor,
and IDEs). Set `SPORTIQ_TRANSPORT=http` to serve the streamable-HTTP endpoint at `/mcp` for
remote/web clients (the hosted instance above runs in this mode).

## Develop

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
npx @modelcontextprotocol/inspector uv run python -m sportiq.server
```

See `CLAUDE.md` for collaboration rules and `docs/index.md` for the wiki entry point.

## Data sources & credits

SportIQ derives some model constants offline from open datasets. Raw datasets are
never shipped or fetched at runtime — only small derived seeds (`circuits.json`,
`venues.json`, `elo_seed.json`) are committed.

- **[F1DB](https://github.com/f1db/f1db)** — Formula 1 database (1950–present),
  licensed **CC BY 4.0**. Used offline to derive per-circuit stop counts and lap
  lengths in `f1/data/circuits.json`; per-circuit pit **loss** is measured offline
  from OpenF1 lap data (in-lap + out-lap vs clean-lap baseline).
- **[Cricsheet](https://cricsheet.org)** — free ball-by-ball IPL match data. Used
  offline to derive measured venue scoring priors (`cricket/data/venues.json`); we
  ship only derived aggregates, never the raw match data.
- **[martj42 international football results](https://github.com/martj42/international_results)**
  — match results 1872–present, **CC0**. Used offline for Elo backtesting.
- **[OpenF1](https://openf1.org)** — free, keyless live F1 telemetry (runtime source).
- **[football-data.org](https://football-data.org)** — free football data; their
  free tier requests a credit link (runtime source).

## License & author

Created and maintained by **Utkarsh Gupta** ([@Ninjabeam20](https://github.com/Ninjabeam20)).

Licensed under the [MIT License](LICENSE) — © 2026 Utkarsh Gupta. You may use, copy,
and modify this software, but the copyright notice and this permission must be retained
in all copies or substantial portions. The canonical package is
[`sportiq-mcp` on PyPI](https://pypi.org/project/sportiq-mcp/) and
`io.github.Ninjabeam20/sportiq-mcp` in the
[official MCP registry](https://registry.modelcontextprotocol.io).
