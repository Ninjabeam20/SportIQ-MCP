---
title: Home-server cutover of the public MCP
type: finding
tags: [home-server, cloudflare, caddy, cloud-run, deploy]
sources: [chat]
last_updated: 2026-08-30
related: [[0012-hosted-abuse-controls]], [[hosted-url-and-release-drift]]
---

# Home-server cutover of the public MCP

A 2026-08-13 decision, model locked 2026-08-23, inventory refreshed 2026-08-30:
move the public SportIQ connector off Cloud Run onto the Dell home server at
`https://sportiq.utkarshgupta.org/mcp`. **Advertised URL is still Cloud Run.**
The public hostname is NXDOMAIN. There is no `sportiq` container and no
`~/stacks/sportiq`. Live Caddy **already contains** a `sportiq.utkarshgupta.org`
block, including the forbidden `header_up CF-Connecting-IP` line — Task 6 must
strip that line, not append a second block. Cloudflare tunnel hostname and GCP
are still untouched.

## Operating model: two systems, one public URL

Until the Dell is **proven**, Claude, ChatGPT, README, SECURITY.md, and
`website/src/config/links.ts` stay on
`https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp`.

1. Keep Cloud Run as the advertised connector while the Dell is stood up.
2. Build SportIQ on the Dell in parallel (compose, one Caddy block, tunnel hostname).
   Invisible to Claude until DNS + tunnel + Caddy serve `/mcp`.
3. Prove the Dell (initialize, tool call, SSE not buffered, 429s on `CF-Connecting-IP`).
   Do not advertise `sportiq.utkarshgupta.org` while it is NXDOMAIN or unproven.
4. Then flip connectors **and** public docs together. Cloud Run stays a day or two
   as rollback.
5. Then delete GCP — only after a second explicit `yes, delete GCP`: Scheduler
   keep-warm → Cloud Run service → Artifact Registry. Not on the first 200 OK.

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
