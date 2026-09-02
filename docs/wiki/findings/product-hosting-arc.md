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
5. **GCP Task 9 teardown (2026-09-02).** Scheduler, Cloud Run, Artifact Registry deleted. Project `sportiq-mcp-prod` shut down (`DELETE_REQUESTED`, billing unlinked). `ey2eariulq` HTTP 404.

## Current (2026-09-02)

| Channel | Reality |
| :--- | :--- |
| Live connector | `https://sportiq.utkarshgupta.org/mcp` (Dell, stateless HTTP, package 0.3.2) |
| Cloud Run / Artifact Registry / project | **deleted** — project `sportiq-mcp-prod` is `DELETE_REQUESTED`, billing off |
| PyPI / `uvx sportiq-mcp` | **0.3.2**; registry remotes = Dell URL |
| Product | every tool free; no SportIQ paywall |

## Do not

- Recreate Cloud Run or `sportiq-keepwarm` on the Dell.
- Advertise any `*.run.app` hostname.
- Copy Cloud Run keep-warm onto the Dell, or set `K_SERVICE` there.
- Re-introduce a Pro gate on `main`. Paid code lives only at tag `v0.2.3`.
- Recreate GCP unless you `gcloud projects undelete sportiq-mcp-prod` within ~30 days.
