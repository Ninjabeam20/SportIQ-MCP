# SportIQ MCP — AI Operating Guide

Read this resource once at session start. It tells you which tools exist, how to use them
efficiently, and how to interpret every response.

---

## Modules at a glance

| Module | Tools | Data scope |
|--------|-------|-----------|
| **Football** | 15 tools | FIFA WC 2026 — groups, fixtures, odds, Monte Carlo bracket |
| **F1** | 13 tools | OpenF1 telemetry, tyre deg, pit strategy, pace comparison |
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

### "Who will win the World Cup 2026?"
1. `football_simulate_bracket()` — 1 call. Returns per-team title probabilities.
   Default 10,000 iterations gives ±2% stable results.

### "Predict Argentina vs France"
1. `football_match_predictor(home_team="ARG", away_team="FRA")` — 1 call.
   Returns most likely scoreline + outcome probabilities.

### "What's the best F1 pit strategy for Verstappen at Monaco?"
1. `f1_get_sessions(year=2025, country="Monaco")` → pick the `session_key` for the race
2. `f1_predict_pit_strategy(session_key=<key>, driver_number=1)`
   — 2 calls.

### "Which F1 drivers are faster at Monaco?"
1. `f1_get_sessions(year=2025, country="Monaco")` → pick `session_key`
2. `f1_head_to_head_pace(session_key=<key>, driver_a=1, driver_b=16)`
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
- Live scorecard TTL: 30 s. Odds TTL: 5 min. Fixtures: 6 h. Standings: 10 min.

---

## Error recovery

| Code | Recovery |
|------|---------|
| `ALL_SOURCES_FAILED` | Tell user data is temporarily unavailable. Check `sources_tried` for context. |
| `NOT_FOUND` | Entity doesn't exist — re-check the team code or match ID. |
| `INVALID_INPUT` | Fix the argument; `message` states what's wrong. |
| `RATE_LIMITED` | Quota exhausted for the day. Advise retrying after midnight UTC. |
| `UPSTREAM_TIMEOUT` | Upstream slow; retry once after 60 s. |

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

Tools that use only static seeds or OpenF1 (which is public/free) work without any key.

---

## Team and player codes

- **IPL teams:** MI, CSK, RCB, KKR, SRH, DC, PBKS, RR, GT, LSG
- **F1 drivers:** use race number (1=Verstappen, 16=Leclerc, 44=Hamilton, 63=Russell, 4=Norris, 81=Piastri, 14=Alonso, 55=Sainz, 11=Perez, 10=Gasly)
- **WC 2026 teams:** 3-letter FIFA codes (ARG, BRA, FRA, ENG, ESP, GER, POR, NED, BEL, ITA, etc.)
- Codes are case-insensitive in all tools.

---

## Batching guidance

- You may call up to 3 tools in parallel when their inputs don't depend on each other.
  E.g. `cricket_get_live_matches()` + `football_get_groups()` can run simultaneously.
- Never call more than 5 tools in a single turn — prefer depth over breadth.
- The flagship intel tools (`cricket_build_dream11_team`, `f1_predict_pit_strategy`,
  `football_simulate_bracket`) already aggregate data internally; do not pre-fetch
  squads or standings before calling them.
