---
title: Cricket Head-to-Head Model
type: model
tags: [cricket, h2h, form, heuristic]
sources: [src/sportiq/cricket/models/head_to_head.py]
last_updated: 2026-10-22
related: [[cricket-head-to-head]], [[form-index]], [[cricket-win-probability]], [[cricket-squad-chain]], [[cricket-player-stats-chain]]
---

# Cricket Head-to-Head Model

`summarise_h2h()` (`cricket/models/head_to_head.py`, pure) scores two squads by per-player form and turns the count of form edges into an estimated head-to-head win rate.

## Inputs
`team_a`, `team_b` (labels only), `squad_a`, `squad_b` (player dicts with `name` and optionally
`player_id`), and `stats_by_player` (`{player_id: raw_stats}` for whichever players the stats chain could
fetch).

## Method
1. Each player gets a [[form-index]] score from their raw stats; a player with no stats gets a neutral
   `form_score = 50`.
2. Both squads are sorted by form, and the i-th ranked player of team A is compared with the i-th of
   team B. Each comparison is an edge for the higher form score.
   Equal scores are no edge; pairing stops at the shorter squad.
3. `h2h_win_rate_a = edges_a / (edges_a + edges_b)` (rounded to 4 dp); with no decisive pairing it is
   0.5 / 0.5. `key_players_*` are each side's top three by form.

## Output
`{team_a, team_b, team_a_edge_count, team_b_edge_count, key_players_a, key_players_b,
h2h_win_rate_a, h2h_win_rate_b}`. The tool [[cricket-head-to-head]] folds it into
[[cricket-win-probability]].

## Caveats
A heuristic, not a fitted model: it ignores batting order, conditions and match history. Players
without fetched stats all sit at 50, so their pairings are ties and the estimate leans on the few
players who do have stats.
