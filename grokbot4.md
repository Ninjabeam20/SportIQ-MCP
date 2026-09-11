# grokbot4 — Docs hygiene + verification

| Field | Value |
|---|---|
| Repo | `sportiq-mcp (Ninjabeam20/SportIQ-MCP)` |
| Branch | `bot` |
| Base SHA | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` |
| Date | 2026-09-11 |
| Scope | Plans only in this commit; no production code yet |

## Goal
Keep wiki/findings honest after fixes and define verification on bot only.

## Non-goals
- No cloudbuild/Cloud Run deploy
- No push

## Safety (binding)
- Implement only on branch `bot` (worktree). Never merge to main, never push, never deploy unless the user explicitly says yes.
- No live scrape / live LLM / live SSH / live paid API hammering unless the user explicitly asks.
- Prefer offline fixtures under `tests/fixtures/**`.
- TDD: failing test first (RED) → minimal fix (GREEN) → tidy.
- Do not stage `.env`, credentials, tokens, or secrets.

## Docs hygiene tasks
### SQ-D1 — Update findings / wiki after fixes

- **Finding ID:** `SQ-D1`
- **File pins:**
  - `docs/wiki/findings/cricapi-envelope-leak.md`
  - `docs/wiki/models/*`
  - `GAPS.md`
- **RED repro idea:** Docs still claim RED after GREEN fixes (or vice versa).
- **Failing-test-first steps:**
  1. After each fix, update the matching finding/model page status on bot.
  2. Do not invent prod deployment claims.
- **Acceptance criteria:**
  - Findings reflect bot reality.
  - No false 'fixed in prod' language.
- **Risk:** Low.
- **Implement only on `bot`:** yes

### SQ-V1 — Verification matrix

- **Finding ID:** `SQ-V1`
- **File pins:**
  - `tests/unit/`
  - `tests/adapters/`
  - `tests/chains/`
  - `tests/tools/`
- **RED repro idea:** N/A
- **Failing-test-first steps:**
  1. Run targeted pytest clusters per Tier.
  2. Confirm branch bot; main==`{sq_base}`.
- **Acceptance criteria:**
  - Tier A/B tests GREEN.
  - main SHA unchanged.
  - audit-fixes dirty files intact.
- **Risk:** Low.
- **Implement only on `bot`:** yes

## Verification matrix
| Gate | Check | Pass |
|---|---|---|
| V1 | pit/value_bet/form_trends/dream11 unit tests | GREEN |
| V2 | fallback/cache/cricapi/not_found tests | GREEN |
| V3 | `git -C .worktrees/bot branch --show-current` | `bot` |
| V4 | `git rev-parse main` | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` unchanged |
| V5 | No edits to Dockerfile/cloudbuild unless asked | true |

## Rollback
- Revert on `bot` only; never reset `audit-fixes` dirty work or `main`.

## Checklist (all unchecked initially)

- [ ] SQ-D1 docs
- [ ] V1–V5
- [ ] Rollback understood
- [ ] No push/deploy
