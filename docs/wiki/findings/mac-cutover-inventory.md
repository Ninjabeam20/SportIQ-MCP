---
title: Mac worktree inventory before home-server apply
type: finding
tags: [home-server, cloud-run, release, inventory]
sources: [chat]
last_updated: 2026-08-30
related: [[home-server-cutover]], [[hosted-url-and-release-drift]], [[0012-hosted-abuse-controls]]
---

# Mac worktree inventory before home-server apply

> **Snapshot (2026-08-30, pre-flip).** Do not treat this page as current
> hosting state. Live connector is `https://sportiq.utkarshgupta.org/mcp`.
> See [[home-server-cutover]] and [[product-hosting-arc]].

Every in-tree change as of 2026-08-30, before commit/push. **At snapshot time
the live connector was still Cloud Run.** Dell compose/Caddy/Cloudflare apply
still needed owner `yes` (that apply later landed the same day).

## Parallel hosts (do not mix)

| Host | Role after this push | Must not happen |
|---|---|---|
| Cloud Run `https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp` | **Live** Claude/ChatGPT/README/`links.ts` | No `gcloud run deploy`, no teardown |
| Dell `sportiq.utkarshgupta.org` | Code ready in git; hostname still NXDOMAIN | No compose up / Caddy reload / tunnel until `yes` |

## Code

- `src/sportiq/core/cache.py` — atomic cache counters (`reserve` / `refund` / `incr_counter_if_below` / `decr_counter`).
- `src/sportiq/core/fallback.py` — quota reserve before fetch, refund on failure.
- `src/sportiq/core/ratelimit.py` — same atomic counter API.
- `src/sportiq/core/request_limits.py` — `SPORTIQ_TRUST_CLOUDFLARE` → `CF-Connecting-IP` (home server). Cloud Run still uses `K_SERVICE` + rightmost XFF.
- `src/sportiq/server.py` — HTTP branch only: `stateless_http = True` (stdio/uvx unchanged).
- `src/sportiq/football/tools.py` — small envelope/odds-sibling alignment.
- `src/sportiq/cricket/tools.py` / `intel_tools.py` — `NOT_FOUND` envelopes; intel NotFound handling.
- `Dockerfile` — `uv pip install --system --frozen` against `uv.lock`; HEALTHCHECK localhost liveness (not a keep-warm). Values unchanged: 30s / 5s / 60s start-period.
- `docker-compose.yml` (**new**) — `sportiq` on external `apps`, **no** `ports:`, `restart: unless-stopped`, always-on idle, no keep-warm sidecar. Not in the sdist allowlist.
- `.env.example` — `SPORTIQ_TRUST_CLOUDFLARE` / `DISKCACHE_DIR` documented, empty.
- `pyproject.toml` / `server.json` / `uv.lock` — package **0.3.2**, `mcp>=1.27.2,<2`.
- `scripts/check_release_build.py` — asserts `server.json` version + Dockerfile `--frozen`.
- `.github/workflows/security.yml` — pip-audit cron addition.
- `.gitignore` — `grok_changes*.md`, `grok_index.md`, `grok_agent.md` stay local.

## Tests

- `tests/unit/test_request_limits.py` — CF identity cases.
- `tests/unit/test_server_http_wiring.py` (**new**) — stateless HTTP wiring.
- `tests/unit/test_ratelimit_atomic.py` — atomic counters.
- `tests/chains/test_chain_respects_budget.py` — reserve/refund.
- `tests/tools/test_odds_tools.py` — sibling keys.
- `tests/tools/test_cricket_h2h.py`, `test_cricket_intel_tools.py`, `test_cricket_value_bets.py` — NotFound envelopes.

## Public docs (advertised URL = Cloud Run only)

- `README.md` / `SECURITY.md` / `website/src/config/links.ts` / `website/CLAUDE.md` / `website/website.md` — replace dead `329580761892` hostname with live `ey2eariulq`. **Do not** point at `sportiq.utkarshgupta.org`.
- `CLAUDE.md` / `AGENTS.md` / `PROJECT.md` / `GAPS.md` / `cloud.md` — production **target** is Dell; **live** URL is Cloud Run; always-on idle; gates `yes` / `flip` / `yes, delete GCP`.
- `docs/wiki/decisions/0012-hosted-abuse-controls.md` — CF identity path.
- `docs/wiki/findings/hosted-url-and-release-drift.md` — dead URL finding.
- `docs/wiki/findings/home-server-cutover.md` — cutover operating model.
- `docs/superpowers/plans/2026-08-13-home-server-migration.md` (**new**) — canonical apply plan.
- `docs/index.md` — finding index lines.

## Dell inventory (read-only, 2026-08-30) — not applied by this commit

- Edge up (caddy + cloudflared). ~5 GiB MemAvailable. No `sportiq` container. No `~/stacks/sportiq`.
- Live Caddyfile **already has** `http://sportiq.utkarshgupta.org` → `sportiq:8080` **with** `header_up CF-Connecting-IP` (must be **removed** on Task 6, not duplicated).
- Public DNS: `sportiq.utkarshgupta.org` NXDOMAIN. Jarvis still Access 302.
- Cloud Run HEAD `/mcp` still 405 (healthy). Keep-warm scheduler stays until Task 9.

## Intentionally not in this commit

- `grok_*.md` (gitignored). Vault `Knowledge/` playbook (not this repo).
- Dell `compose up`, Caddy reload, Cloudflare hostname, connector flip, GCP delete, PyPI `v0.3.2` tag.
