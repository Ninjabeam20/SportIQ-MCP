---
title: Product and hosting arc (GCP → paid → free → home server)
type: finding
tags: [hosting, cloud-run, home-server, monetization, history]
sources: [chat, cloud.md, 0011-pro-entitlement-gate, home-server-cutover]
last_updated: 2026-09-02
related: [[0011-pro-entitlement-gate]], [[home-server-cutover]], [[hosted-url-and-release-drift]], [[mac-cutover-inventory]]
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

## Current (2026-09-02)

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

## Do not

- Set `K_SERVICE` on the Dell. Do not copy `sportiq-keepwarm` (no cron, sidecar, or `/mcp` pinger).
- Recreate Cloud Run, re-link a GCP billing card, or advertise any `*.run.app` hostname.
- Re-introduce a Pro gate on `main`. Paid code lives only at tag `v0.2.3`.
- Treat `gcloud projects undelete` as a live failback — the billing card is gone too.
