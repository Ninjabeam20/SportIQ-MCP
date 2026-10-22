# SportIQ MCP — AI Operating Guide

Read this resource once at session start. It tells you which tools exist, how to use them
efficiently, and how to interpret every response.

---

## Modules at a glance

| Module | Tools | Data scope |
|--------|-------|-----------|
| **Football** | 16 tools | FIFA WC 2026 — groups, fixtures, odds, Monte Carlo bracket, what-if replay |
| **F1** | 14 tools | OpenF1 telemetry, tyre deg, pit strategy, pace comparison, title-race simulator |
| **Cricket** | 14 tools | IPL live scores, squads, odds, fantasy XI, probability edge |
| **Cross-sport** | 1 tool | Joint multi-match model across football + cricket |
| **Core** | 1 tool | Health / quota status |

---

## Minimum-call recipes

These are the most common user intents. Follow the call sequence exactly — do not add
extra informational calls unless the user explicitly asks for them.

### "Best fantasy XI for MI vs CSK"
1. `cricket_build_dream11_team(team_a="MI", team_b="CSK", venue="wankhede")`
   — 1 call. Returns 11 players + captain + VC + total credits.

### "Who should I captain for tonight's IPL match?"
1. `cricket_get_live_matches()` → pick the `match_id` for the relevant match
2. `cricket_captain_recommendation(match_id=<id>)`
   — 2 calls.

### "Compare model vs market for today's cricket"
1. `cricket_find_value_bets()` — 1 call. Returns matches with edge > 0.

### "Who won the World Cup 2026?" / "How did the model do?"
1. `football_simulate_bracket()` — 1 call. The tournament ended with the
   2026-07-19 final. Read `meta.mode`: `completed` means real results were
   replayed and `meta.champion` is the actual winner; `pre_tournament_prior`
   means no result data was available, so the output is only the model's
   pre-tournament view, not a forecast.

### "What if France had beaten Spain in the semi-final?"
1. `football_what_if(replay_from="final", flip_winner_of="ESP-FRA")` — 1 call.
   Keeps the real results before `replay_from`, flips that tie's winner, simulates the rest.

### "Who can still win the F1 drivers' title?"
1. `f1_simulate_championship(year=2026)` — 1 call. Title probabilities plus exact
   mathematical elimination (`eliminated: true` means the title is out of reach).

### "Predict Argentina vs France"
1. `football_match_predictor(home_team="ARG", away_team="FRA")` — 1 call.
   Returns most likely scoreline + outcome probabilities.

### "What was the best pit strategy for Norris in the latest Grand Prix?"
1. `f1_get_sessions(year=2026, session_name="Race", latest_completed=True)` → its `session_key` (e.g. `11353`, the 2026 Dutch GP)
2. `f1_predict_pit_strategy(session_key=<key>, driver_number=1)`
   — 2 calls.

### "Which F1 drivers were faster at the Dutch GP?"
1. `f1_get_sessions(year=2026, country="Netherlands", session_name="Race")` → pick `session_key`
2. `f1_head_to_head_pace(session_key=<key>, driver_a=1, driver_b=3)`
   — 2 calls.

### "Build me a multi-match model"
1. `cross_sport_build_accumulator()` — 1 call. Combines the top model-vs-market edges across cricket + football.

### "How healthy is the server / how much quota is left?"
1. `sportiq_health()` — 1 call. Shows cache backend, adapter status, per-source quota.

### "What's the WC group stage situation?"
1. `football_get_groups()` — 1 call for group draw and format.
2. Add `football_get_standings()` only if the user wants live standings.

---

## Response envelope — always present

Every tool returns one of two shapes:

**Success:**
```json
{
  "data": { "...tool-specific payload..." },
  "meta": {
    "source": "cricapi",
    "is_stale": false,
    "data_age_seconds": 12,
    "fallback_used": false,
    "duration_ms": 187,
    "estimated": true
  }
}
```

**Error:**
```json
{
  "error": {
    "code": "ALL_SOURCES_FAILED | NOT_FOUND | INVALID_INPUT | RATE_LIMITED | UPSTREAM_TIMEOUT",
    "message": "Human-readable explanation",
    "sources_tried": [{"name": "cricapi", "error": "429"}],
    "suggestion": "What to try next"
  }
}
```

---

## Staleness rules

- `meta.is_stale: true` → data is from cache beyond the fresh TTL. Tell the user:
  "As of about X minutes ago…" and advise retrying in a few minutes.
- `meta.estimated: true` → output is model-generated (ILP solver, Monte Carlo, tyre fit).
  Qualify with "model estimate" in your response.
- Cricket live scorecard TTL: 30 s. Odds TTL: 5 min. Football fixtures: 6 h (the WC 2026 is over).
  F1 completed-session laps/stints: 24 h. Standings: 10 min.

---

## Error recovery

| Code | Recovery |
|------|---------|
| `ALL_SOURCES_FAILED` | Tell user data is temporarily unavailable. Check `sources_tried` for context. |
| `NOT_FOUND` | Entity doesn't exist — re-check the team code or match ID. |
| `INVALID_INPUT` | Fix the argument; `message` states what's wrong. |
| `RATE_LIMITED` | Defined but not currently emitted: budget exhaustion surfaces as `ALL_SOURCES_FAILED` with `skipped` / `rate_limited` attempts. Advise retrying after midnight UTC. |
| `UPSTREAM_TIMEOUT` | The call hit the per-tool deadline (30 s by default); upstreams were slow or a simulation was queued. Retry once after 60 s. |

---

## API key requirements

Some data sources need keys set in the server environment. If a tool returns
`ALL_SOURCES_FAILED` with `"error": "MissingCredentialsError"` in `sources_tried`,
tell the user to set the appropriate key:

| Key | Needed for |
|-----|-----------|
| `CRICAPI_KEY` | Live cricket scores, schedules, squads |
| `APIFOOTBALL_KEY` | Football fixtures and standings |
| `THEODDS_KEY` | Live market odds (cricket + football) |
| `FOOTBALLDATA_KEY` | football-data.org World Cup endpoints (they return 403 without it) |

Tools that use only static seeds or historical OpenF1 sessions (keyless) work without any key.
Live-session OpenF1 telemetry needs paid authentication, which SportIQ does not wire.

---

## Team and player codes

- **IPL teams:** MI, CSK, RCB, KKR, SRH, DC, PBKS, RR, GT, LSG
- **F1 drivers:** use race number. 2026 examples: 1=Norris, 3=Verstappen, 12=Antonelli, 16=Leclerc, 44=Hamilton, 63=Russell, 81=Piastri. Driver numbers change by season; use `f1_get_drivers(session_key)` for the session's list.
- **WC 2026 teams:** 3-letter FIFA codes of the 48 entrants (ARG, BRA, FRA, ENG, ESP, GER, POR, NED, BEL, MAR, USA, etc.); `football_get_groups()` lists them all.
- Codes are case-insensitive in all tools.

---

## Batching guidance

- You may call up to 3 tools in parallel when their inputs don't depend on each other.
  E.g. `cricket_get_live_matches()` + `football_get_groups()` can run simultaneously.
- Never call more than 5 tools in a single turn — prefer depth over breadth.
- The flagship intel tools (`cricket_build_dream11_team`, `f1_predict_pit_strategy`,
  `football_simulate_bracket`) already aggregate data internally; do not pre-fetch
  squads or standings before calling them.
