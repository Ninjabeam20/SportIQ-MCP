---
title: 2026-10-22 Full Audit and the 2026-10-10 Model Audit
type: finding
tags: [audit, security, performance, correctness, football, f1, cricket]
sources: [docs/audits/2026-10-22-full-audit.md, docs/audits/2026-10-10-sports-model-audit.md, docs/audits/2026-10-10-sports-model-calculations.json]
last_updated: 2026-10-22
related: [[diskcache-expire-purge]], [[stateless-lifespan-teardown]], [[live-conditioning]], [[pit-strategy]], [[dream11-scoring]], [[value-bet]], [[product-hosting-arc]]
---

# 2026-10-22 Full Audit and the 2026-10-10 Model Audit

Two read-only audits of `main`: a five-agent platform audit on 2026-10-22 (security, runtime, performance, docs, deployment) and a sports-model correctness audit on 2026-10-10 that recomputed SportIQ's football, F1 and cricket outputs against the real 2026 competitions.

## Source files
- `docs/audits/2026-10-22-full-audit.md`: findings P0–P3, deployment, architecture, efficiency and
  opportunities.
- `docs/audits/2026-10-10-sports-model-audit.md` with `docs/audits/2026-10-10-sports-model-calculations.json`:
  per-sport recomputations. Its opener: the discrepancies came from incomplete identities, obsolete
  squads, lost results and incorrect arithmetic, which neither re-ranking nor more iterations would fix.

`docs/audits/` is kept local until the fixes deploy, then committed. Neither the audits nor this page
reproduce host addresses or credentials.

## P0 findings (2026-10-22) and their fixes
| Finding | Fix |
| :-- | :-- |
| Any rate-limit counter increment purged the diskcache | [[diskcache-expire-purge]] |
| Per-request lifespan teardown (11 production `AttributeError`s) | [[stateless-lifespan-teardown]], plus `/healthz` |
| CricAPI / The Odds API keys logged in plain text by httpx at INFO | `httpx`/`httpcore` loggers at WARNING; redaction now runs after the contextvars merge, recurses into nested values, and catches a bare `apikey=` |
| Home-server network identity in a tracked plan doc (public repo) | Redacted going forward; no history rewrite. The firewall check is an owner action |
| Website metadata pointed at a parked domain; `og.png` missing | Website reconciliation (domain + OG image) |

## P1/P2 highlights and their fixes
- **Latency:** sims and the CBC solve moved to `asyncio.to_thread`; 30 s per-tool deadline returning
  `UPSTREAM_TIMEOUT`; 15 s total budget per chain; 10 s CBC time limit; cache reads/writes fail open.
- **Security CI:** dependency bumps (mcp ≥ 1.30, pyjwt, urllib3, certifi, pillow), an audit of what the
  image actually ships, and a release gate (lint + coverage) with SHA-pinned actions.
- **Inputs:** cricket/football team resolvers, provider venue strings, `"Group A"`, OpenF1 404 → NOT_FOUND,
  `INTERMEDIATE` = `INTER`.
- **Football (10-10):** the replay lost extra-time and penalty winners, two team aliases, and the KSA/SAU
  key ([[live-conditioning]]); value bets now require positive EV ([[value-bet]]).
- **F1 (10-10):** the pit decision now sums the remaining race for both options, race length comes from
  the regulation distance, and compound legality and the rain threshold are fixed ([[pit-strategy]]).
- **Cricket (10-10):** Dream11 scoring now follows the official T20 profile ([[dream11-scoring]]); squads are
  generated from Cricsheet; credits and ownership are labelled heuristics.
- **Data freshness:** static-seed cache keys carry the package version; TTLs follow the post-tournament
  state.

## What was deliberately not changed
The `gather` re-raise in `cross_sport_build_accumulator` (recorded decision: keep unexpected failures
visible), DNS-rebinding protection off, scrapers opt-in, diskcache as a healthy state, and the
coverage gate living in CI only.
