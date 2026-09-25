---
title: Home-server cutover of the public MCP
type: finding
tags: [home-server, cloudflare, caddy, cloud-run, deploy]
sources: [chat]
last_updated: 2026-09-25
related: [[0012-hosted-abuse-controls]], [[hosted-url-and-release-drift]], [[mac-cutover-inventory]], [[product-hosting-arc]]
---

# Home-server cutover of the public MCP

Task 8 flipped 2026-08-30. **Live connector is**
`https://sportiq.utkarshgupta.org/mcp`. Task 9 (2026-09-02) deleted Cloud Run
`sportiq-mcp`, scheduler `sportiq-keepwarm`, and Artifact Registry
`cloud-run-source-deploy`. Former `*.run.app` URLs 404. GCP billing card
removed by the owner the same day.

Dell `sportiq` container is healthy on `apps`, Caddy block has
`flush_interval -1` and **no** `header_up CF-Connecting-IP`, tunnel public
hostname `sportiq` → `http://caddy:80`, no Access app on this hostname.

## Operating model after flip

1. Claude / ChatGPT / README / `links.ts` advertise the Dell URL.
2. Cloud Run, keep-warm, and Artifact Registry are gone (Task 9). Recovery is
   rebuild from historical `cloud.md`, not failback.

## Locked shape

Internet → Cloudflare (orange cloud) → tunnel `home-server` → Caddy `:80` →
container `sportiq:8080` on Docker network `apps`. No host ports, no router
forward, **no Cloudflare Access** (Claude/ChatGPT connectors cannot complete
Access login). Jarvis stays behind Access.

Rate limits trust `CF-Connecting-IP` via `SPORTIQ_TRUST_CLOUDFLARE=1`. **Never**
set `K_SERVICE` on the Dell. **Never** copy `sportiq-keepwarm` (no cron, sidecar,
or `/mcp` pinger). Do not add Caddy `header_up CF-Connecting-IP` (empties
the header on non-tunnel requests and collapses every client into one 429 bucket).
One replica, diskcache volume, scrapers off, no Redis.
Always-on idle (`restart: unless-stopped`): MCP only computes on a tool call.
Cloud Run `sportiq-keepwarm` was deleted with Task 9.
The production transport uses MCP SDK 1.x Streamable HTTP with stateless
sessions (`mcp<2`). SDK v2 would be a separate migration, not a cutover step.

## Do not

- Apply the full vault `Caddyfile.intended` (it also changes `www` and dead routes).
  Live Caddy still 301s `www` to HTTP apex and still routes `jobs`/`video`/`outfit`.
- The historical Task 8 rule was to wait for the Dell smoke checks before
  changing README / `links.ts`; that flip completed on 2026-08-30.
- Tear down the Dell without another host. There is no Cloud Run failback.
  Historical URL (404): `https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp`.
- Copy `sportiq-keepwarm` onto the Dell, or stop the container until the next
  request. Idle listen is the heat/latency trade-off (2026-08-30).

## Plans

- Canonical: `docs/superpowers/plans/2026-08-13-home-server-migration.md`
- Overlay `grok_changes8.md`–`grok_changes13.md` (local-only). Tasks 5–9 are
  done (2026-09-02): Dell is live; GCP project `sportiq-mcp-prod` is
  `DELETE_REQUESTED`.
