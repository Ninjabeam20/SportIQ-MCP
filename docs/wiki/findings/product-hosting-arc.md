---
title: Product and hosting arc (GCP → paid → free → home server)
type: finding
tags: [hosting, cloud-run, home-server, monetization, history]
sources: [chat, cloud.md, 0011-pro-entitlement-gate, home-server-cutover]
last_updated: 2026-09-02
related: [[0011-pro-entitlement-gate]], [[home-server-cutover]], [[hosted-url-and-release-drift]], [[mac-cutover-inventory]]
---

# Product and hosting arc (GCP → paid → free → home server)

One-page timeline of how SportIQ was hosted and sold. Read this when GitHub, Cloud Run, and the home server seem to disagree — that is usually history, not a bug. Do not treat this page as permission to delete GCP.

**Confused about progress?** Start here, then [[0011-pro-entitlement-gate]] (paywall), [[home-server-cutover]] (Dell flip), [[hosted-url-and-release-drift]] (dead URL). `docs/log.md` is the local journal (gitignored).

## Timeline

1. **Hosted on Google Cloud Run (free tier).** Public streamable-HTTP at `/mcp` so Claude.ai / ChatGPT could connect without a local install. Runbook: repo `cloud.md`. Scale-to-zero plus a keep-warm scheduler existed only because Cloud Run sleeps.
2. **Paid / Pro plan (~2026-06-20).** INTEL tools gated behind `SPORTIQ_PRO_KEY` (V1 honor-system, then V2a hosted shared-key). RAW tools and `sportiq_health` stayed free. Design: [[0011-pro-entitlement-gate]].
3. **Paywall reversed (2026-07-01).** The gate produced $0 MRR / 0 sponsors and a high `SUBSCRIPTION_REQUIRED` failure rate (~41% of tool calls). All gate code was deleted from `main`. Free edition shipped as `0.3.0`. Paid edition is preserved at git tag **`v0.2.3`**. GitHub Sponsors remains a donation — nothing unlocks. SportIQ stayed on **Cloud Run, fully free**.
4. **Home-server migration (2026-08).** Production live is the Dell Compose stack behind Cloudflare Tunnel + Caddy: `https://sportiq.utkarshgupta.org/mcp`. Cutover: [[home-server-cutover]]. Cloud Run `https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp` stays **rollback until the owner says `yes, delete GCP`**. Project shutdown is a third, named-project decision — not part of Task 9.

## Current (2026-09-02)

| Channel | Reality |
| :--- | :--- |
| Live connector | `https://sportiq.utkarshgupta.org/mcp` (Dell, stateless HTTP, package 0.3.2) |
| Rollback | Cloud Run `ey2eariulq` — keep until `yes, delete GCP` |
| PyPI / `uvx sportiq-mcp` | still **0.3.1** until an owner tags `v0.3.2` |
| Product | every tool free; no SportIQ paywall |

## Do not

- Delete Cloud Run, the keep-warm scheduler, or Artifact Registry without `yes, delete GCP`.
- Advertise the old `329580761892` Cloud Run hostname (NXDOMAIN). See [[hosted-url-and-release-drift]].
- Copy Cloud Run keep-warm onto the Dell, or set `K_SERVICE` there.
- Re-introduce a Pro gate on `main`. Paid code lives only at tag `v0.2.3`.
