# grokbot1 — INDEX + safety

| Field | Value |
|---|---|
| Repo | `sportiq-mcp (Ninjabeam20/SportIQ-MCP)` |
| Branch | `bot` |
| Base SHA | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` |
| Date | 2026-09-11 |
| Scope | Plans only in this commit; no production code yet |

## Goal
Index diagnosis-driven bot-branch work for SportIQ-MCP and bind safety before code changes.

## Non-goals
- No merges to `main`
- No push / Cloud Run deploy / cloudbuild without explicit yes
- No live paid sports API calls in unit tests

## Safety (binding)
- Implement only on branch `bot` (worktree). Never merge to main, never push, never deploy unless the user explicitly says yes.
- No live scrape / live LLM / live SSH / live paid API hammering unless the user explicitly asks.
- Prefer offline fixtures under `tests/fixtures/**`.
- TDD: failing test first (RED) → minimal fix (GREEN) → tidy.
- Do not stage `.env`, credentials, tokens, or secrets.

## Plan map
| File | Theme |
|---|---|
| `grokbot1.md` | INDEX + safety |
| `grokbot2.md` | Tier A crashes |
| `grokbot3.md` | Tier B empty-200 cache poison + CricAPI unwrap + IN_PLAY |
| `grokbot4.md` | Docs hygiene + verification |

## Operating mode
- Work in `.worktrees/bot` on `bot` (base `5cfa12ff2d8eabd10a279074b3e3b1107e38886d`).
- Leave dirty `audit-fixes` checkout intact.
- Use `tests/fixtures/**` and recorded adapters only.

## Ranked overview
1. Tier A: pit compound, gather envelopes, cricket NotFound, Dream11 CBC, value-bet, form-trends int
2. Tier B: empty-200 cache poison, CricAPI unwrap, IN_PLAY
3. Docs hygiene + verification

## Checklist (all unchecked initially)

- [ ] Read grokbot2–4 before coding
- [ ] Worktree branch == bot; main SHA unchanged
- [ ] No Cloud Run / push
