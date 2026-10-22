---
title: Product and hosting arc (GCP → paid → free → home server)
type: finding
tags: [hosting, cloud-run, home-server, monetization, history, uptime, waf]
sources: [chat, cloud.md, 0011-pro-entitlement-gate, home-server-cutover]
last_updated: 2026-10-22
related: [[0011-pro-entitlement-gate]], [[home-server-cutover]], [[hosted-url-and-release-drift]], [[mac-cutover-inventory]], [[stateless-lifespan-teardown]], [[sportiq-health]]
---

# Product and hosting arc (GCP → paid → free → home server)

One-page timeline of how SportIQ was hosted and sold. Read this when GitHub and the home server seem to disagree — that is usually history, not a bug. Task 9 GCP resource teardown is done.

**Confused about progress?** Start here, then [[0011-pro-entitlement-gate]] (paywall), [[home-server-cutover]] (Dell flip), [[hosted-url-and-release-drift]] (dead URL). `docs/log.md` is the local journal (gitignored).

## Timeline

1. **Hosted on Google Cloud Run (free tier).** Public streamable-HTTP at `/mcp` so Claude.ai / ChatGPT could connect without a local install. Runbook: repo `cloud.md`. Scale-to-zero plus a keep-warm scheduler existed only because Cloud Run sleeps.
2. **Paid / Pro plan (~2026-06-20).** INTEL tools gated behind `SPORTIQ_PRO_KEY` (V1 honor-system, then V2a hosted shared-key). RAW tools and `sportiq_health` stayed free. Design: [[0011-pro-entitlement-gate]].
3. **Paywall reversed (2026-07-01).** The gate produced $0 MRR / 0 sponsors and a high `SUBSCRIPTION_REQUIRED` failure rate (~41% of tool calls). All gate code was deleted from `main`. Free edition shipped as `0.3.0`. Paid edition is preserved at git tag **`v0.2.3`**. GitHub Sponsors remains a donation — nothing unlocks. SportIQ stayed on **Cloud Run, fully free**.
4. **Home-server migration (2026-08).** Production live is the Dell Compose stack behind Cloudflare Tunnel + Caddy: `https://sportiq.utkarshgupta.org/mcp`. Cutover: [[home-server-cutover]].
5. **GCP Task 9 teardown (2026-09-02).** Scheduler, Cloud Run, Artifact Registry deleted. Project `sportiq-mcp-prod` shut down (`DELETE_REQUESTED`, billing unlinked). Owner also removed the GCP billing card. `ey2eariulq` HTTP 404.

## Current (2026-09-25)

| Channel | Reality |
| :--- | :--- |
| Live connector | `https://sportiq.utkarshgupta.org/mcp` (Dell, stateless HTTP, package 0.3.2) |
| Cloud Run / Artifact Registry / project | **deleted** — project `sportiq-mcp-prod` is `DELETE_REQUESTED`; billing account/card removed |
| PyPI / `uvx sportiq-mcp` | **0.3.2**; official MCP registry remotes = Dell URL |
| Glama listing | Dell URL after owner GitHub sync (2026-09-02) |
| Product | every tool free; no SportIQ paywall |

## Final check (2026-09-02)

Dell git matches `origin/main`, one replica, `K_SERVICE` unset, scrapers off, Redis unset,
JSONL on, Caddy `flush_interval -1` / no `header_up CF-Connecting-IP`. Public
initialize 200 / 0.3.2 / stateless; GET `/mcp` 406; `sportiq_health` diskcache
ok; 44 tools. `ey2eariulq` HTTP 404. Old `329580761892` host NXDOMAIN. Local
`uv run pytest` green. Never set `K_SERVICE`. Never copy `sportiq-keepwarm`.

## 2026-09-25 push, verify, deploy cycle

`main` and its local `origin/main` tracking ref are at `0bc1232`. Dell git was
reported at the same commit after the documentation sync; its container was
rebuilt from `5e9a4fa`, the last code commit. The later two commits are docs
only. Post-merge local checks reported 871 collected tests, 91.91% coverage,
Ruff and release-build pass. The Dell container and public MCP initialize,
44-tool list, diskcache health, and 500-iteration bracket simulation passed in
the deployment smoke check. GitHub Actions status for `0bc1232` has not been
verified from this repository snapshot. Source changes after the `v0.3.2` tag
are deployed on Dell but are not part of the published PyPI 0.3.2 artifact.

## Uptime alerting (owner runbook, D14 — 2026-10-22)

Nothing alerted on the historical Cloudflare 530s (tunnel could not reach the origin). Since
opus cook1, the server exposes `GET /healthz`: a liveness-only route that returns `200 ok`
without touching the cache, chains or network (see [[stateless-lifespan-teardown]]). The
Docker HEALTHCHECK probes it on localhost. External checks may call it too; the rule is
`GET /healthz` at **≥ 5-minute** intervals, never `/mcp`, and never a keep-warm or scheduler
on the host.

The owner sets this up in a dashboard (agents must not):

1. **Cloudflare Health Checks** (preferred, same account as the tunnel): Cloudflare dashboard →
   the `utkarshgupta.org` zone → Traffic → Health Checks → Create.
   - URL: `https://sportiq.utkarshgupta.org/healthz`, method `GET`, expected code `200`.
   - Interval: 5 minutes. Retries: 2. Timeout: 5 s.
   - Notifications → add an email notification for this health check (healthy ↔ unhealthy).
2. **Or UptimeRobot** (free tier): new HTTP(s) monitor on the same URL, 5-minute interval,
   keyword `ok` optional, alert contact = owner email.

Verify: the check shows "healthy" within one interval; stop the container on the Dell once to
confirm an alert email arrives, then restart it.

## Cloudflare WAF rate limit (owner runbook, D13 — 2026-10-22)

App-level limits (60 requests/client/minute, 300/process/minute, 1 MiB bodies; see GAPS #1)
stay as defence in depth. An edge rule stops abusive clients before they reach the tunnel.

Owner steps: Cloudflare dashboard → `utkarshgupta.org` zone → Security → WAF → Rate limiting
rules → Create rule.
- **Match:** hostname equals `sportiq.utkarshgupta.org` **and** URI path contains `/mcp`
  ("contains" covers both `/mcp` and the legacy `/u/<key>/mcp` paths).
- **Rate:** 60 requests per 1 minute, counted per IP (Cloudflare's client IP characteristic).
- **Action:** Block, duration 1 minute.
- Leave `/healthz` and the website out of the rule.

Verify: from one machine, more than 60 `POST /mcp` in a minute gets a Cloudflare 429/block page;
normal connector use is unaffected.

## Do not

- Set `K_SERVICE` on the Dell. Do not copy `sportiq-keepwarm` (no cron, sidecar, or `/mcp` pinger).
- Recreate Cloud Run, re-link a GCP billing card, or advertise any `*.run.app` hostname.
- Re-introduce a Pro gate on `main`. Paid code lives only at tag `v0.2.3`.
- Treat `gcloud projects undelete` as a live failback — the billing card is gone too.
