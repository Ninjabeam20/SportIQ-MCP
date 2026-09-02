---
title: Home-server cutover of the public MCP
type: finding
tags: [home-server, cloudflare, caddy, cloud-run, deploy]
sources: [chat]
last_updated: 2026-08-30
related: [[0012-hosted-abuse-controls]], [[hosted-url-and-release-drift]], [[mac-cutover-inventory]], [[product-hosting-arc]]
---

# Home-server cutover of the public MCP

Task 8 flipped 2026-08-30. **Live connector is**
`https://sportiq.utkarshgupta.org/mcp`. Cloud Run
`https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp` stays as rollback until
Task 9 (`yes, delete GCP`).

Dell `sportiq` container is healthy on `apps`, Caddy block has
`flush_interval -1` and **no** `header_up CF-Connecting-IP`, tunnel public
hostname `sportiq` → `http://caddy:80`, no Access app on this hostname.

## Operating model after flip

1. Claude / ChatGPT / README / `links.ts` advertise the Dell URL.
2. Cloud Run stays up a day or two as rollback (do not delete on the first 200).
3. Delete GCP only after a second explicit `yes, delete GCP`: Scheduler
   keep-warm → Cloud Run service → Artifact Registry.

## Locked shape

Internet → Cloudflare (orange cloud) → tunnel `home-server` → Caddy `:80` →
container `sportiq:8080` on Docker network `apps`. No host ports, no router
forward, **no Cloudflare Access** (Claude/ChatGPT connectors cannot complete
Access login). Jarvis stays behind Access.

Rate limits trust `CF-Connecting-IP` via `SPORTIQ_TRUST_CLOUDFLARE=1`. Do not set
`K_SERVICE` on the Dell. Do not add Caddy `header_up CF-Connecting-IP` (empties
the header on non-tunnel requests and collapses every client into one 429 bucket).
One replica, diskcache volume, scrapers off, no Redis.
Always-on idle (`restart: unless-stopped`): MCP only computes on a tool call;
do not add a keep-warm cron on the Dell and do not auto-sleep (Cloud Run
`sportiq-keepwarm` exists only because GCP scales to zero).
Stay on MCP SDK 1.x Streamable HTTP; SDK v2 is a follow-up after the hostname
is proven. Stateless HTTP is already landed (`grok_changes13.md`).

## Do not

- Apply the full vault `Caddyfile.intended` (it also changes `www` and dead routes).
  Live Caddy still 301s `www` to HTTP apex and still routes `jobs`/`video`/`outfit`.
- Point README / `links.ts` at `sportiq.utkarshgupta.org` before Task 8 flip
  (that would repeat the dead-URL bug in [[hosted-url-and-release-drift]]).
- Tear down Cloud Run on the first public 200. Rollback URL:
  `https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp`.
- Copy `sportiq-keepwarm` onto the Dell, or stop the container until the next
  request. Idle listen is the heat/latency trade-off (2026-08-30).

## Plans

- Canonical: `docs/superpowers/plans/2026-08-13-home-server-migration.md`
- Overlay `grok_changes8.md`–`grok_changes13.md` (local-only). Mac code is Tasks 1–4;
  Dell/Cloudflare needs owner `yes` (Tasks 5–7 prove); connectors+docs need `flip`
  (Task 8); GCP delete needs `yes, delete GCP` (Task 9).
