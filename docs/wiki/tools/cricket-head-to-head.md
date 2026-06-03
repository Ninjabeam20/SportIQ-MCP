---
title: Cricket Head-to-Head Analyzer
type: tool
tags: [cricket, h2h, analytics, win-probability]
sources: [cricket-squad-chain, cricket-player-stats-chain, cricket-win-probability-model, form-index]
last_updated: 2026-06-03
related: [[cricket-player-form-index]], [[cricket-win-probability-model]], [[form-index]], [[cricket-squad-chain]], [[cricket-player-stats-chain]]
---

# Cricket Head-to-Head Analyzer

Compares two cricket teams head-to-head using per-player form scores derived from squad and player-stats chain data, then folds the result into a win-probability estimate.

## Tool signature

```python
async def cricket_head_to_head(team_a: str, team_b: str) -> dict
```

### Inputs

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `team_a` | `str` | First team code or name (e.g. `"MI"`, `"India"`). |
| `team_b` | `str` | Second team code or name (e.g. `"CSK"`, `"Australia"`). |

### Output (`data`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `team_a` | `str` | Echo of the input team A label. |
| `team_b` | `str` | Echo of the input team B label. |
| `team_a_edge_count` | `int` | Number of positional player matchups won by team A on form. |
| `team_b_edge_count` | `int` | Same for team B. |
| `key_players_a` | `list` | Top-3 players from team A by form score, `[{name, form_score}]`. |
| `key_players_b` | `list` | Same for team B. |
| `h2h_win_rate_a` | `float` | Estimated H2H win rate for team A from edge ratio (0.0–1.0). |
| `h2h_win_rate_b` | `float` | Same for team B; `h2h_win_rate_a + h2h_win_rate_b == 1.0`. |
| `win_prob_a` | `float` | Final win probability for team A from [[cricket-win-probability-model]]. |
| `win_prob_b` | `float` | Same for team B; `win_prob_a + win_prob_b == 1.0`. |

`meta.estimated: true` always — all outputs are model estimates, not oracle data.

## Data flow

```
squad_chain (team_a) ─┐
squad_chain (team_b) ─┤
                       ├─→ summarise_h2h() ─→ win_prob() ─→ {data, meta}
player_stats_chain    ─┘
  (best-effort, ≤22 players, asyncio.gather semaphore=5)
```

1. Fetch both squads via [[cricket-squad-chain]]. On `AllSourcesFailedError` → `ALL_SOURCES_FAILED` envelope.
2. For every player in both squads that has a `player_id` (up to 11 per side), fire concurrent stats fetches via [[cricket-player-stats-chain]] gated by `_PLAYER_STATS_SEMAPHORE(5)`. Failures are silently dropped.
3. `summarise_h2h()` in `cricket/models/head_to_head.py` scores each player via `player_form_index(raw)` (from [[form-index]]), ranks players by form within each squad, counts positional edges, and derives `h2h_win_rate_*` from the edge ratio.
4. `win_prob({"h2h_win_rate": h2h_a}, {"h2h_win_rate": h2h_b})` converts H2H rates to final probabilities weighted 30% H2H / 50% form (neutral) / 20% venue (neutral).

## Graceful degradation

| Condition | Behaviour |
| :--- | :--- |
| No `player_id` on any player | All form scores default to 50 (neutral); H2H is 50/50. |
| Some stats fetches fail | Those players fall back to form_score=50; rest scored normally. |
| All stats fetches fail | All players neutral; tool still returns a valid envelope. |
| Squad chain fails for either team | `ALL_SOURCES_FAILED` error envelope. |

## Validation

- `team_a` empty or whitespace → `INVALID_INPUT`.
- `team_b` empty or whitespace → `INVALID_INPUT`.
- `team_a.strip().lower() == team_b.strip().lower()` → `INVALID_INPUT "team_a and team_b must be different."`.
