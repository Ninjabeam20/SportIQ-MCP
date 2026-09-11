# grokbot4 — Docs hygiene + verification

| Field | Value |
|---|---|
| Repo | `sportiq-mcp (Ninjabeam20/SportIQ-MCP)` |
| Branch | `bot` |
| `main` SHA (must stay) | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` |
| Recheck date | 2026-09-11 |
| Recheck model | `cursor-grok-4.6-high` (NORMAL, not fast) |
| Scope | Plans only in the recheck commit; Composer 2.5 runs this after Tier A/B code |

## Goal
Keep wiki/findings/GAPS honest after **residual** fixes. Verify on `bot` only.

## Non-goals
- No cloudbuild / Cloud Run / Dell deploy
- No merge to `main`
- This recheck did **not** edit wiki/GAPS (markdown plans only)

## Safety (binding)
Same as grokbot1. `docs/log.md` is gitignored — append locally after impl if the file exists on the operator machine; **do not `git add` it**. Wiki pages that you do edit need YAML frontmatter (`.claude/rules/wiki-conventions.md`).

## Recheck notes (2026-09-11)

- Original V3 (`git -C .worktrees/bot branch`) is **invalid here**. Use repo-root git.
- Original V4 `{sq_base}` placeholder is `main` = `5cfa12ff2d8eabd10a279074b3e3b1107e38886d`.
- `cricapi-envelope-leak` finding is **already written as fixed**. After Composer 2.5, do not mark it RED again. Optionally set `last_updated` only if you add a regression test.
- Wiki `docs/wiki/models/form-trends.md` disagrees with code today (`recent_trend` ≥6 vs code ≥4; xG `0.0` vs `None`). Fix wiki to match code in SQ-D1; do not change the ≥4 behavior (comment in `form_trends.py` L81–83 is intentional).
- GAPS.md #3 “cricket tools catch NotFound everywhere” is **over-broad** until SQ-A3 lands.

---

### SQ-D1 — Update findings / wiki after fixes

- **Finding ID:** `SQ-D1`
- **File pins:**
  - `docs/wiki/findings/cricapi-envelope-leak.md` — already GREEN; only touch if SQ-B2 gained a test
  - `docs/wiki/models/pit-strategy.md` — after SQ-A1: one sentence on None/unknown compound → MEDIUM; None rainfall → 0
  - `docs/wiki/models/form-trends.md` — match code: ≥4 matches for trend; xG `None` when absent; finished-status gate after A6/B3
  - `docs/wiki/models/value-bet.md` — `find_value` skips non-positive / non-numeric prices; `implied_prob` still raises on `<= 0`
  - `docs/wiki/models/dream11-solver.md` — missing CBC → `InvalidInputError` (after A4)
  - `GAPS.md` #3 — after A3: cricket RAW live/schedule/odds(/squad mock) catch `NotFoundError`; do not claim football/F1 are still uncaught
  - `docs/index.md` — only if a finding title/one-liner changes
- **Failing-test-first:** N/A (docs). Do this **after** the matching code GREEN, not before.
- **Acceptance:**
  - Findings describe **bot** reality. No “fixed in prod”, no Cloud Run as live, no `*.run.app`.
  - Live connector if mentioned: `https://sportiq.utkarshgupta.org/mcp`.
  - Wiki frontmatter `last_updated: 2026-09-11` (or impl date) on pages you edit.
- **Do not:** edit `docs/raw/`; invent new findings for GREEN-already items; retune Elo.
- **Risk:** Low.
- **Implement only on `bot`:** yes

---

### SQ-V1 — Verification matrix

- **Finding ID:** `SQ-V1`
- **File pins:** test dirs below — run **clusters**, not a coverage-failing local `--cov-fail-under`.
- **Commands (repo root, branch `bot`):**

```bash
git branch --show-current   # must be bot
git rev-parse main          # must be 5cfa12ff2d8eabd10a279074b3e3b1107e38886d
git diff main -- Dockerfile cloudbuild.yaml docker-compose.yml
```

Targeted pytest (after the matching finding):

```bash
# A1
uv run pytest tests/unit/test_pit_strategy.py -q
# A4
uv run pytest tests/unit/test_dream11_solver.py -q
# A5
uv run pytest tests/unit/test_value_bet.py -q
# A6 + B3 form
uv run pytest tests/unit/test_form_trends.py tests/tools/test_football_form_trends.py tests/unit/test_results_state.py -q
# A3
uv run pytest tests/tools/test_cricket_raw_tools.py tests/chains/test_chain_not_found.py -q
# B1
uv run pytest tests/adapters/test_football_data_org.py tests/adapters/test_api_football.py tests/unit/test_fallback_chain.py -q
# B2 verify
uv run pytest tests/adapters/test_cricapi.py -q
# A2 verify (do not rewrite on fail without reading grokbot2)
uv run pytest tests/tools/test_f1_intel_tools.py tests/unit/test_tool_telemetry.py -q
```

Optional full `uv run pytest` before stopping; CI still owns `--cov-fail-under=84`. Always `uv sync --extra dev --extra analytics` if the env is cold (plain `uv sync` drops extras).

- **Acceptance:**
  - Named clusters GREEN for findings you implemented.
  - `main` SHA unchanged.
  - `git diff main` has **no** Dockerfile / cloudbuild / compose deploy bits unless the user asked.
  - No `.env` staged (`git status`).
- **Risk:** Low.
- **Implement only on `bot`:** yes

## Verification matrix

| Gate | Check | Pass |
|---|---|---|
| V1 | A1/A4/A5/A6 unit tests above | GREEN after those findings |
| V2 | A3 + B1 + B2 tests above | GREEN after those findings |
| V3 | `git branch --show-current` | `bot` |
| V4 | `git rev-parse main` | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` unchanged |
| V5 | No Dockerfile/cloudbuild/compose edits unless asked | true |
| V6 | Recheck model was `cursor-grok-4.6-high` not fast | recorded in grokbot1 |

## Rollback
- Revert **on `bot` only** (`git revert` of the impl commit(s)). Never reset `main`. There is no `audit-fixes` branch on origin to protect.

## Composer 2.5 stop conditions
- Stop after ranked residuals + D1 + this matrix. Do not pick up GAPS #10 Redis re-probe, sdist allowlist, or hosting docs.
- Do not publish to PyPI. Do not bump version for these bugfixes unless the user asks for a release.

## Checklist

- [ ] SQ-D1 docs after each GREEN finding
- [ ] V1–V6
- [ ] Rollback understood (`bot` only)
- [ ] No merge to `main` / no deploy
