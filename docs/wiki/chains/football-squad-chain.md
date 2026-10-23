---
title: Football Squad Chain
type: chain
tags: [football]
sources: []
last_updated: 2026-10-22
related: [[api-football]], [[static-seed]], [[football-get-squad]]
---

# Football Squad Chain

`FallbackChain` powering football tools.

## Resolution order
api-football -> static-seed

| Adapter | Enabled by default |
| :-- | :-- |
| [[api-football]] | Yes — when APIFOOTBALL_KEY set |
| [[static-seed]] | Yes — terminator; bundles **no** football squads |

## TTLs
- Fresh: 12h
- Stale ceiling: 3d

## Cache key
`sportiq:football:squad:{team_hash}` — the lowercased team value is hashed with an 8-byte BLAKE2s digest.

No football rosters are bundled: the hand-written 8-team seed was removed on 2026-10-22 (no
hand-curated player data). The static terminator returns an empty-but-valid squad, and
`football_get_squad` copies its note into `meta.note`: "No bundled squads; set APIFOOTBALL_KEY for live
squads." [[api-football]] needs a numeric team id; a FIFA code is refused before any request.
