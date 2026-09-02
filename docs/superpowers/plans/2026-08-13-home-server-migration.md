# SportIQ Home-Server Migration Implementation Plan

> **STATUS 2026-09-02: DONE.** Live connector is
> `https://sportiq.utkarshgupta.org/mcp` (Dell). Tasks 5–8 applied. Task 9
> deleted Cloud Run / scheduler / Artifact Registry. Project `sportiq-mcp-prod`
> is `DELETE_REQUESTED` (billing unlinked). Do not `gcloud run deploy`. Do not
> advertise `*.run.app`. The body below is the original apply plan (keep as
> history). Rollback to Cloud Run is no longer possible.

> **Grok overlay (2026-08-13, model locked 2026-08-23):** `grok_changes8.md` (index + agent brief + Task 0 inventory) → `grok_changes9.md` (identity) → `grok_changes10.md` (Compose/HEALTHCHECK) → `grok_changes11.md` (vault + steel docs) → `grok_changes12.md` (gated Dell / flip / GCP). Stay on tree `mcp>=1.27.2,<2`; do not pin `mcp==1.27.1`. HEALTHCHECK uses exec-form `python -c` (Docker flattens the draft's `def _ok()`). **Two systems, one public URL** until Task 8 — see Operating model.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **This is a NEW STACK deploy**, not a portfolio rebuild, not a Jarvis rebuild, and not a blanket `Caddyfile.intended` apply. The only Caddy change is adding one `sportiq` hostname block to whatever is *live* on the server after you have read that live file. Do not "fix www" or drop dead routes in the same change.

**Goal:** Move the public SportIQ MCP endpoint off Google Cloud Run onto the Dell home server, behind the existing Cloudflare Tunnel → Caddy → Docker `apps` network, with no router port-forward, no published app ports, and no anonymous exposure of Jarvis.

**Architecture:** Same container image the Cloud Run Dockerfile already builds (`SPORTIQ_TRANSPORT=http`, `/mcp` on `:8080`). New root `docker-compose.yml` joins the external `apps` network with `container_name: sportiq` and **no** `ports:`. Caddy reverse-proxies `http://sportiq.utkarshgupta.org` → `sportiq:8080`. Cloudflare Tunnel publishes that hostname explicitly to `HTTP caddy:80`. Public TLS stays at Cloudflare. App-level rate limits start trusting Cloudflare's `CF-Connecting-IP` via `SPORTIQ_TRUST_CLOUDFLARE=1` (today they only trust `X-Forwarded-For` when `K_SERVICE` is set, so on the home server every client would collapse into Caddy's Docker IP). Cloud Run stays the **only advertised URL** until Task 8. GCP teardown is Task 9 and needs its own `yes, delete GCP`.

**Tech Stack:** Existing SportIQ FastMCP HTTP server (`mcp>=1.27.2,<2`, locked 1.29.0, **stateless** streamable-HTTP), Docker Compose, Caddy 2, Cloudflare Tunnel `home-server`, diskcache (no Redis), Ubuntu Server 26.04 on the Dell.

## Operating model (locked): two systems, one public URL

This is intentional, not a delay. Until the Dell is **proven**, Claude, ChatGPT, the website, README, SECURITY.md, and `website/src/config/links.ts` keep using

`https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp`.

1. **Keep Cloud Run.** Nobody switches connectors while we stand up the Dell.
2. **Build SportIQ on the Dell in parallel.** Same image, `docker-compose.yml`, one Caddy block for `sportiq.utkarshgupta.org`, Cloudflare tunnel hostname. That stack is invisible to Claude until DNS + tunnel + Caddy actually serve `/mcp`.
3. **Prove the Dell (Task 7).** Initialize handshake, a tool call, SSE body not empty/buffered, 429s keyed on Cloudflare IP. Until that evidence is green, `sportiq.utkarshgupta.org` stays unpublished in README / `links.ts`. Advertising it while NXDOMAIN (or while unproven) repeats the dead-URL bug.
4. **Then flip (Task 8).** Owner says `flip` after seeing Task 7 evidence. Point Claude's custom connector (and ChatGPT, and public docs) at `https://sportiq.utkarshgupta.org/mcp`. Leave Cloud Run up a day or two as rollback: if the tunnel or Dell dies, switch the connector URL back.
5. **Then delete GCP (Task 9).** Only after a **second** explicit `yes, delete GCP`. Order: Scheduler keep-warm → Cloud Run service → Artifact Registry, so billing actually goes to zero. Not on the first 200 OK. Project shutdown is a third, separate decision.

Nothing on the Dell, Caddy, Cloudflare, or GCP gets applied until the owner says `yes` in the same message. Mac-side code (compose, `SPORTIQ_TRUST_CLOUDFLARE`, steel docs that describe the *target*) can sit in git without touching production.

| Gate | Phrase in the same message | What it covers |
|---|---|---|
| Stand up + prove | `yes` | Tasks 5–7: clone, `.env`, `compose up`, one Caddy block, Cloudflare hostname, curl prove. Public URL **unchanged**. |
| Flip | `flip` | Task 8: Claude + ChatGPT connectors **and** README / `links.ts` / SECURITY / steel-doc live URL. Cloud Run stays. |
| Teardown | `yes, delete GCP` | Task 9: scheduler → Cloud Run → Artifact Registry, then billing-report check. |

## Global Constraints

- Owner: Utkarsh. Mac writes code. Dell laptop is the headless server (`ssh home-server` → user `ninjabeam20`, LAN `192.168.29.66`).
- **Do not deploy, ssh apply, reload Caddy, change Cloudflare, rotate keys, flip connectors/docs, or delete GCP resources unless the owner says the matching phrase in the same message** (`yes` / `flip` / `yes, delete GCP`). Inventory SSH (read-only) is allowed in Task 0.
- Never commit, print, or paste secrets (`.env`, tunnel token, Resend, OpenRouter, `gcal-sa.json`, SportIQ provider keys).
- Never port-forward on the router. Never publish app ports on the host (`ports:` is forbidden on the SportIQ compose file). Never expose Jarvis anonymously. Do not add Cloudflare Access to Jarvis's allow-list as a side effect.
- Docker only on the host; no `apt install` of SportIQ, Python, CBC, or uv on the Ubuntu OS. CBC stays inside the image (already in the Dockerfile).
- Do not inspect `~/stacks/edge/.env` (TUNNEL_TOKEN).
- Do not use `Knowledge/Projects/home-server/default_setup.md` (stale `/srv`, `web` network, bare-repo hooks).
- Hostname is **`sportiq.utkarshgupta.org`**. Connector URL becomes `https://sportiq.utkarshgupta.org/mcp`. Do not use `mcp.` unless the owner changes this.
- **No Cloudflare Access** on `sportiq.utkarshgupta.org`. Claude.ai / ChatGPT custom connectors cannot complete Access OTP. This hostname is a public MCP endpoint, like the apex portfolio, not like Jarvis.
- **Do not combine this move with MCP Python SDK v2 / spec `2026-07-28`.** Stay on tree `mcp>=1.27.2,<2` (locked 1.29.0). The `mcp<2` pin is what enforces this.
- **Stateless is IN scope as of 2026-08-15 and is already landed** (`grok_changes13.md`). Supersedes the original draft line, which said "stay with sessions, stateless is a follow-up". Stateless is **not** an SDK v2 feature and never required one: `FastMCP.__init__` on the locked 1.29.0 already accepts `stateless_http=` (verified by `inspect.signature`). v2 is a rewrite (`FastMCP` → `MCPServer`); stateless is one setting. Only the second is being taken. Reason it moved into scope: the home server rebuilds in place, and session-holding connectors break on every rebuild. `json_response` stays `False`.
- Do not apply the full vault `Caddyfile.intended` as part of this work. That file also changes `www` and comments dead routes. SportIQ only **adds** one server block. Confirm the live `~/stacks/edge/Caddyfile` before editing.
- Cloudflare Free-plan wildcard tunnel routes are unreliable. Add `sportiq.utkarshgupta.org` as an **explicit** published hostname. `530` / `1033` = hostname missing from tunnel routes.
- `docker-compose.yml` is a new repo-root file and must **not** be added to `pyproject.toml` sdist `include` or `scripts/check_release_build.py` allowlists (sdist is an allowlist; leaving it off is correct).
- Never call live sports APIs from tests. Never set `REDIS_URL`. Never enable `SPORTIQ_ENABLE_NDTV` / `SPORTIQ_ENABLE_CRICBUZZ` on the public host.
- Do not set `K_SERVICE` on the home container (that flag means "this is Cloud Run" and would trust spoofable `X-Forwarded-For`).
- Rate counters stay process-local. Run **one** SportIQ replica. Do not `deploy.replicas` > 1 and do not start a second compose project for the same image.
- **Always-on idle (2026-08-30).** `restart: unless-stopped`. MCP already only computes on a tool call; the container just listens. Do **not** add a keep-warm cron/sidecar hitting `/mcp` on the Dell (that is a Cloud Run scale-to-zero hack; delete it in Task 9). Do **not** auto-sleep or wake-on-request: scipy/numpy import is 15–60s and is why Claude connectors hung on Cloud Run cold start. Leave the Dockerfile HEALTHCHECK as localhost liveness.
- First image build needs ~2 GB RAM (scipy/numpy/pandas, same class of pain as the portfolio standalone build). Abort the build if `MemAvailable` is under 1500 MiB.
- Commits only when the owner asks. Push only when the owner asks. Connector/docs flip only on `flip`. GCP teardown only on `yes, delete GCP`.
- **Do not add `header_up CF-Connecting-IP` in Caddy.** Caddy already forwards the inbound header. Setting it empties the header on non-tunnel requests and collapses every client into Caddy's Docker IP (one 429 bucket).

## Out of scope (do not do in this plan)

- MCP SDK v2 (`FastMCP` → `MCPServer`), protocol `2026-07-28`.
- `json_response=True` (plain JSON instead of SSE framing — removes streaming; not worth it for the simulation tools).
- Resumability via `event_store`.

`stateless_http=True` was previously listed here. It is **no longer out of scope** — see the constraint above and `grok_changes13.md`.
- Applying the whole `Caddyfile.intended` (www HTTPS fix, dropping `jobs`/`video`/`outfit`).
- Portfolio rebuild, Jarvis rebuild, Syncthing, Open WebUI, Redis/Memorystore.
- Moving provider keys out of env into a secrets manager.
- Changing Cloud Run while it is still the production connector URL, except the final teardown task.
- Keep-warm cron / Cloud Scheduler clone on the Dell; auto-sleep, wake-on-request, or Docker socket activation for `sportiq`.

## Locked security decisions

1. **Edge:** Internet → Cloudflare (orange cloud) → tunnel `home-server` → `cloudflared` (outbound only) → Caddy `:80` → `sportiq:8080` on network `apps`.
2. **Public MCP, private keys:** the hostname is unauthenticated (connectors require that). Provider keys on the server are optional; default is **no live cricket/odds keys** so strangers cannot burn CricAPI / The Odds API quota. Flagship tools (bracket sim, F1 pit strategy, Dream11) work without those keys. `FOOTBALLDATA_KEY` + `SPORTIQ_FOOTBALL_LIVE_ELO=1` may be copied if the owner wants WC live results to match Cloud Run; that is an owner paste into server `.env`, never into git.
3. **Client IP for 429s:** `CF-Connecting-IP` only, via `SPORTIQ_TRUST_CLOUDFLARE=1`. Do not trust `X-Forwarded-For` on the home server.
4. **Caddy SSE:** `flush_interval -1` on this reverse_proxy so Streamable HTTP is not buffered.
5. **Keep `/u/<key>/mcp`:** `LegacyKeyPathMiddleware` stays; old sponsor connector URLs must still rewrite to `/mcp`.
6. **Logs:** JSON inside the container (`SPORTIQ_LOG_FORMAT=json`), docker json-file rotation `10m` × 3 files. No Cloud Logging dashboard unless the owner asks later.
7. **Cache:** named volume `sportiq-cache` at `DISKCACHE_DIR=/var/cache/sportiq` so quota counters and TTLs survive rebuilds. diskcache is healthy; do not flag it as degraded.
8. **Always-on idle:** the container stays up. Heat is from real tool calls (bracket sim, CBC), not from listening. `mem_limit: 1536m` is a cap, not a reservation. No keep-warm pinger.

## File map

| File | Role |
|---|---|
| `src/sportiq/core/request_limits.py` | Trust `CF-Connecting-IP` when `SPORTIQ_TRUST_CLOUDFLARE` is on |
| `tests/unit/test_request_limits.py` | Regression: CF IP used; XFF ignored on home; spoofed CF ignored when flag off |
| `docker-compose.yml` | Home-server Compose: `sportiq` on `apps`, no `ports:` |
| `Dockerfile` | HEALTHCHECK against local `/mcp` (406/405/400 count as alive) |
| `.env.example` | Document `SPORTIQ_TRUST_CLOUDFLARE` and `DISKCACHE_DIR` (no secrets) |
| `cloud.md` | Mark Cloud Run as rollback; point at home-server cutover. Keep the Cloud Run URL as the live connector until Task 8. |
| `README.md` / `SECURITY.md` / `website/src/config/links.ts` | Public URL swap at **Task 8 flip**, not after the first public 200 |
| `docs/log.md` | Append after code lands, after prove, after flip, after teardown |
| Vault `Knowledge/Projects/home-server/Caddyfile.intended` | Add the sportiq block to *intended* (not live apply). No `header_up CF-Connecting-IP`. |
| Vault `Knowledge/Context/infrastructure.md` | DNS may exist after Task 7; mark `sportiq.` **live** only after Task 8 flip |
| Server `~/stacks/sportiq/` | Git clone of `Ninjabeam20/SportIQ-MCP` (created at deploy time) |
| Server `~/stacks/sportiq/.env` | chmod 600, owner-pasted, never copied off the box |
| Server `~/stacks/edge/Caddyfile` | Live router; add one block only, owner apply |

---

## Agent brief (paste this to a deploy agent)

```
Mission: NEW STACK — SportIQ MCP onto the Dell home server.

You are deploying sportiq, not portfolio, not Jarvis.
Do not apply the full Caddyfile.intended. Only add one hostname block
after you have read the LIVE ~/stacks/edge/Caddyfile.

Hard stops (matching phrase in the same message):
- yes: docker compose up, Caddy reload, Cloudflare tunnel/DNS (Tasks 5–7)
- flip: Claude/ChatGPT connector URL + public docs (Task 8)
- yes, delete GCP: scheduler → Cloud Run → Artifact Registry (Task 9)
- also always gated: key rotation, git push, router changes.

Never: commit/print/paste secrets; inspect ~/stacks/edge/.env;
port-forward on the router; publish host ports; touch Jarvis Access;
set K_SERVICE; enable NDTV/Cricbuzz scrapers; add Redis; upgrade mcp
to SDK v2; use Knowledge/Projects/home-server/default_setup.md.

Hostname: sportiq.utkarshgupta.org
MCP URL:  https://sportiq.utkarshgupta.org/mcp
Access:   PUBLIC (no Cloudflare Access — connectors cannot log in)
Network:  apps (external). Edge stays cloudflared + caddy.
Container name: sportiq   Internal port: 8080
Server path: ~/stacks/sportiq
Git: https://github.com/Ninjabeam20/SportIQ-MCP
Compose: repo-root docker-compose.yml (no ports:)
Idle: always-on listen, no keep-warm cron, no auto-sleep
Trust: SPORTIQ_TRUST_CLOUDFLARE=1  (CF-Connecting-IP, not XFF)

Follow docs/superpowers/plans/2026-08-13-home-server-migration.md
in the sportiq-mcp repo, task by task.

Without owner yes: Task 0 inventory only (SSH read-only).
Mac code tasks 1–4 may proceed in the git worktree without SSH apply.
After Tasks 5–7 prove is green: STOP. Do not flip connectors or README.
```

---

### Task 0: Read-only inventory (no writes)

**Files:**
- Read only on Mac: this plan, `Dockerfile`, `src/sportiq/server.py`, vault `Knowledge/Projects/home-server/Caddyfile.intended`, `Knowledge/Context/infrastructure.md`
- Read only on server: live Caddyfile, compose ps, free memory

**Interfaces:**
- Consumes: SSH alias `home-server`
- Produces: a written inventory in the agent reply (container names, live Caddy hostnames, MemAvailable). Abort deploy tasks if SportIQ-named container already exists or MemAvailable < 1500 MiB

- [ ] **Step 1: Confirm you will not change anything**

Do not run `docker compose up`, `caddy reload`, `git pull` on the server, or any `scp` of a Caddyfile.

- [ ] **Step 2: SSH connectivity**

```bash
ssh home-server 'whoami; hostname; uname -a'
```

Expected: user `ninjabeam20`, Ubuntu.

- [ ] **Step 3: Edge + RAM + existing stacks**

```bash
ssh home-server 'free -h; echo ---; docker compose -f ~/stacks/edge/docker-compose.yml ps; echo ---; docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"; echo ---; docker network inspect apps --format "{{range .Containers}}{{.Name}} {{end}}"'
```

Expected: `caddy` and `cloudflared` up. **No `0.0.0.0:` published ports on app containers** (empty Ports column, or only docker-internal). Record `MemAvailable`. If a container named `sportiq` already exists, stop and ask the owner.

- [ ] **Step 4: Copy the live Caddyfile off the server for diffing (contents only, no secrets)**

```bash
ssh home-server 'cat ~/stacks/edge/Caddyfile'
```

Expected: `auto_https off` and `http://…` blocks. As of 2026-08-30 the live file
**already has** `http://sportiq.utkarshgupta.org` with `flush_interval -1` **and**
the forbidden `header_up CF-Connecting-IP` line. Do not append a second block;
Task 6 edits that block in place (backup first) and deletes the `header_up
CF-Connecting-IP` line. Leave `www` and dead `jobs`/`video`/`outfit` routes.
**Do not inspect `~/stacks/edge/.env`.**

- [ ] **Step 5: Confirm tunnel hostname gap from the Mac (public)**

```bash
curl -sI https://sportiq.utkarshgupta.org/ | head -n 20
```

Expected today: Cloudflare `530` / error 1033, DNS NXDOMAIN, or similar — hostname is not published yet. If it already returns an app 200, stop and ask the owner.

---

### Task 1: Cloudflare client identity for home-server rate limits

**Files:**
- Modify: `src/sportiq/core/request_limits.py`
- Modify: `tests/unit/test_request_limits.py`
- Test: `tests/unit/test_request_limits.py`

**Interfaces:**
- Consumes: existing `_client_identity(scope, *, trust_forwarded: bool) -> str` and `RequestLimitMiddleware.trust_forwarded = bool(os.getenv("K_SERVICE"))`
- Produces: `_client_identity(scope, *, trust_forwarded: bool, trust_cloudflare: bool = False) -> str` which prefers a valid `CF-Connecting-IP` when `trust_cloudflare` is true; `RequestLimitMiddleware.trust_cloudflare` from env `SPORTIQ_TRUST_CLOUDFLARE` in `{1,true,yes,on}` (case-insensitive)

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_request_limits.py` (keep every existing test; do not rename `_client_identity` kwargs already used):

```python
def test_client_identity_uses_cf_connecting_ip_when_trust_cloudflare():
    scope = {
        "headers": [
            (b"cf-connecting-ip", b"203.0.113.50"),
            (b"x-forwarded-for", b"198.51.100.9, 10.0.0.2"),
        ],
        "client": ("172.18.0.4", 1234),
    }
    assert (
        _client_identity(scope, trust_forwarded=False, trust_cloudflare=True)
        == "203.0.113.50"
    )


def test_client_identity_ignores_cf_connecting_ip_when_flag_off():
    scope = {
        "headers": [(b"cf-connecting-ip", b"203.0.113.50")],
        "client": ("172.18.0.4", 1234),
    }
    assert (
        _client_identity(scope, trust_forwarded=False, trust_cloudflare=False)
        == "172.18.0.4"
    )


def test_client_identity_ignores_invalid_cf_connecting_ip():
    scope = {
        "headers": [(b"cf-connecting-ip", b"not-an-ip")],
        "client": ("172.18.0.4", 1234),
    }
    assert (
        _client_identity(scope, trust_forwarded=False, trust_cloudflare=True)
        == "172.18.0.4"
    )


async def test_request_limit_home_proxy_uses_cf_ip_not_xff():
    app = _RecordingApp()
    middleware = _middleware(app, client=1)
    middleware.trust_forwarded = False
    middleware.trust_cloudflare = True

    first = await _request(
        middleware,
        headers=[
            (b"cf-connecting-ip", b"203.0.113.50"),
            (b"x-forwarded-for", b"198.51.100.9"),
        ],
    )
    rejected = await _request(
        middleware,
        headers=[
            (b"cf-connecting-ip", b"203.0.113.50"),
            (b"x-forwarded-for", b"198.51.100.99"),
        ],
    )
    other = await _request(
        middleware,
        headers=[(b"cf-connecting-ip", b"203.0.113.51")],
    )

    assert _status(first) == 200
    assert _status(rejected) == 429
    assert _status(other) == 200
    assert app.calls == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/utkarsh/Documents/Internships_Jobs/sportiq-mcp
uv run pytest tests/unit/test_request_limits.py -q --tb=short
```

Expected: FAIL — `_client_identity()` got an unexpected keyword argument `trust_cloudflare` (or always returns the peer IP).

- [ ] **Step 3: Implement the minimal identity change**

Replace `_client_identity` and the `trust_forwarded` assignment in `RequestLimitMiddleware.__init__` / `__call__` in `src/sportiq/core/request_limits.py` with:

```python
def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _client_identity(
    scope: dict, *, trust_forwarded: bool, trust_cloudflare: bool = False
) -> str:
    """Cloudflare CF-Connecting-IP, else Cloud Run rightmost XFF, else peer."""
    if trust_cloudflare:
        cf_ip = _header(scope, b"cf-connecting-ip").strip()
        if cf_ip:
            try:
                return str(ipaddress.ip_address(cf_ip))
            except ValueError:
                pass

    if trust_forwarded:
        forwarded = _header(scope, b"x-forwarded-for")
        candidate = forwarded.rsplit(",", 1)[-1].strip()
        if candidate:
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                pass

    client = scope.get("client")
    if isinstance(client, (tuple, list)) and client:
        return str(client[0])
    return "unknown"
```

In `RequestLimitMiddleware.__init__`, after `self.global_per_minute = global_per_minute`:

```python
        self.trust_forwarded = bool(os.getenv("K_SERVICE"))
        self.trust_cloudflare = _truthy_env("SPORTIQ_TRUST_CLOUDFLARE")
```

(Remove the old `self.trust_forwarded = bool(os.getenv("K_SERVICE"))` line that currently sits alone.)

In `__call__`, change the identity line to:

```python
        identity = _client_identity(
            scope,
            trust_forwarded=self.trust_forwarded,
            trust_cloudflare=self.trust_cloudflare,
        )
```

Do not change body-size, 429, or replay logic.

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/unit/test_request_limits.py -q --tb=short
uv run ruff check src/sportiq/core/request_limits.py tests/unit/test_request_limits.py
```

Expected: PASS, ruff clean.

- [ ] **Step 5: Commit (only if the owner asked to commit)**

```bash
git add src/sportiq/core/request_limits.py tests/unit/test_request_limits.py
git commit -m "$(cat <<'EOF'
fix(http): trust CF-Connecting-IP for home-server rate limits

Cloud Run used K_SERVICE + rightmost XFF. Behind Caddy the peer is the
proxy, so per-client 429s need Cloudflare's connecting IP instead.
EOF
)"
```

---

### Task 2: Home-server Compose file + env example + healthcheck

**Files:**
- Create: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `Dockerfile` (HEALTHCHECK only; do not change the pip install layers)

**Interfaces:**
- Consumes: existing `Dockerfile` `ENV SPORTIQ_TRANSPORT=http PORT=8080` and `CMD ["python", "-m", "sportiq.server"]`
- Produces: Compose service `sportiq` (`container_name: sportiq`, port 8080 internal, external network `apps`, `env_file: .env`, cache volume, no `ports:`)

- [ ] **Step 1: Create `docker-compose.yml` at the repo root**

```yaml
services:
  sportiq:
    build: .
    container_name: sportiq
    restart: unless-stopped
    env_file: .env
    environment:
      SPORTIQ_TRANSPORT: http
      PORT: "8080"
      SPORTIQ_LOG_FORMAT: json
      SPORTIQ_TRUST_CLOUDFLARE: "1"
      DISKCACHE_DIR: /var/cache/sportiq
    volumes:
      - sportiq-cache:/var/cache/sportiq
    networks: [apps]
    mem_limit: 1536m
    pids_limit: 256
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    # NO ports: — Caddy reaches sportiq:8080 on the apps network only.

networks:
  apps:
    external: true

volumes:
  sportiq-cache:
```

- [ ] **Step 2: Append to `.env.example` (comments on their own lines; no trailing inline comments)**

```
# --- Home-server HTTP (Cloudflare Tunnel + Caddy) ---
# Set to 1 when the process sits behind Cloudflare so rate limits key on
# CF-Connecting-IP. Leave unset on Cloud Run (K_SERVICE + XFF) and on stdio.
SPORTIQ_TRUST_CLOUDFLARE=
# Override diskcache location (Compose mounts /var/cache/sportiq).
DISKCACHE_DIR=
```

Also add a blank-line comment block at the top of the new section reminding operators: public hostname must not enable NDTV/Cricbuzz scrapers.

- [ ] **Step 3: Add HEALTHCHECK to `Dockerfile` after `EXPOSE 8080`**

Do not touch the `FROM` / `apt-get` / `pip install` layers. Insert:

```dockerfile
# GET /mcp is 406 without MCP Accept headers; that still means the process is up.
# Exec-form so Docker does not flatten `def _ok():` into a SyntaxError.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.error, urllib.request\nreq = urllib.request.Request('http://127.0.0.1:8080/mcp')\ntry:\n    urllib.request.urlopen(req, timeout=4)\n    sys.exit(0)\nexcept urllib.error.HTTPError as e:\n    sys.exit(0 if e.code in (400, 405, 406) else 1)\nexcept Exception:\n    sys.exit(1)"]
```

- [ ] **Step 4: Confirm sdist still cannot ship the compose file**

```bash
uv run python scripts/check_release_build.py
```

Expected: exit 0. `docker-compose.yml` must not appear as an allowlist violation *inside* an archive (it must simply be absent from the sdist). If the script fails because a new root file leaked into the sdist, stop — hatch `include` is an allowlist and should already omit it; do not add compose to the allowlist.

- [ ] **Step 5: Commit (only if the owner asked)**

```bash
git add docker-compose.yml .env.example Dockerfile
git commit -m "$(cat <<'EOF'
chore(deploy): add home-server Compose stack with no published ports

SportIQ joins the existing apps network for Caddy. Cache lives in a
volume. Cloudflare connecting-IP trust is on by default in Compose.
EOF
)"
```

---

### Task 3: Vault intended Caddy block + operator docs (no live reload)

**Files:**
- Modify: `/Users/utkarsh/Documents/Internships_Jobs/Knowledge/Projects/home-server/Caddyfile.intended`
- Modify: `cloud.md` (repo)
- Create: `/Users/utkarsh/Documents/Internships_Jobs/Knowledge/Projects/sportiq-mcp/home-server-deploy.md` (vault playbook)
- Modify: `docs/log.md`

**Interfaces:**
- Consumes: live Caddy style `http://<host> { reverse_proxy <container>:<port> }`
- Produces: intended block for `sportiq.utkarshgupta.org` → `sportiq:8080` with SSE flush; playbook the deploy agent follows

- [ ] **Step 1: Append this block to the vault intended Caddyfile (do not scp it yet)**

Add at the end of `Knowledge/Projects/home-server/Caddyfile.intended`:

```
# SportIQ MCP — public connectors (Claude / ChatGPT). No Cloudflare Access.
# Connector URL: https://sportiq.utkarshgupta.org/mcp
http://sportiq.utkarshgupta.org {
	reverse_proxy sportiq:8080 {
		# Do not buffer Streamable HTTP / SSE.
		flush_interval -1
		header_up X-Forwarded-Proto https
	}
}
```

**Do not add `header_up CF-Connecting-IP {http.request.header.CF-Connecting-IP}`.**
Caddy already forwards the inbound header. The explicit `header_up` *sets* the
header to empty on any request that arrives without one (Task 6 curls, LAN),
so `_client_identity` falls back to Caddy's Docker IP and every client shares
one 429 bucket. Leave the header alone. Do not wrap this site in a global
`encode` / gzip of `text/event-stream`.

Do not uncomment `jobs` / `video` / `outfit`. Do not change the `www` block in this task if you are also editing live Caddy later — intended may already have the HTTPS www fix; leave it as-is.

- [ ] **Step 2: Write the vault playbook**

Create `Knowledge/Projects/sportiq-mcp/home-server-deploy.md` with YAML frontmatter and these facts only (no tokens, no keys):

```markdown
---
type: playbook
status: active
project: sportiq-mcp
created: 2026-08-13
---

# SportIQ on the home server

Public MCP: `https://sportiq.utkarshgupta.org/mcp`
Container: `sportiq:8080` on Docker network `apps`
Deploy dir: `~/stacks/sportiq` (git clone, not Syncthing, not `/srv`)
Auth: public hostname, no Cloudflare Access
Compose: repo `docker-compose.yml` — no `ports:`
Secrets: `~/stacks/sportiq/.env` chmod 600, never in git
Edge apply: add one Caddy block; validate; owner reloads Caddy
Tunnel: explicit public hostname `sportiq.utkarshgupta.org` → HTTP `caddy:80`
```

Include the verify ladder from Task 6. Point at this plan for the full command list.

- [ ] **Step 3: Retitle Cloud Run in `cloud.md`**

At the top of `cloud.md`, after the first paragraph, add a short callout (do not delete the old runbook; it is the rollback path until GCP is gone):

```markdown
> **Hosting as of 2026-08-13:** production **target** is the home server
> (`https://sportiq.utkarshgupta.org/mcp`), not Cloud Run. Cutover is **not
> live** until Task 8 flip. This file remains the Cloud Run
> rollback/teardown runbook. Do not `gcloud run deploy` unless
> you are deliberately failing back.
```

Do not put the Cloud Run URL deletion into README/SECURITY/`links.ts` yet (that is Task 8, after Task 7 prove is green and the owner says `flip`).

- [ ] **Step 4: Append `docs/log.md`**

```markdown
## [2026-08-13] decision | migrate public MCP from Cloud Run to home server

Plan: `docs/superpowers/plans/2026-08-13-home-server-migration.md`.
Target hostname `sportiq.utkarshgupta.org` (public, no Access). Compose on
`apps` with no host ports. Rate limits will trust `CF-Connecting-IP`.
SDK v2 / stateless MCP is explicitly deferred. No live Caddy/Cloudflare/GCP
change in this decision.
```

---

### Task 4: Mac-side verification before any server write

**Files:**
- Test: full unit suite for the middleware plus ruff on touched Python

- [ ] **Step 1: Run focused then full tests**

```bash
cd /Users/utkarsh/Documents/Internships_Jobs/sportiq-mcp
uv run pytest tests/unit/test_request_limits.py tests/unit/test_client_info_middleware.py tests/unit/test_config.py -q
uv run ruff check src/sportiq/core/request_limits.py tests/unit/test_request_limits.py
```

Expected: pass.

- [ ] **Step 2: Optional local image build on the Mac (not the Dell)**

```bash
docker compose config
```

Expected: valid YAML, service `sportiq`, no `ports` published to the host.

Do not `docker compose up` on the Mac unless the owner wants a local smoke; the Mac is not on network `apps`.

**HARD STOP.** Tasks 5–7 need an explicit owner `yes` in the same chat message. Task 8 needs `flip` after Task 7 evidence. Task 9 needs `yes, delete GCP`. Stop here and report: files changed, inventory, and the exact apply commands you will run.

---

### Task 5: Server clone + `.env` + compose up (needs owner yes)

**Files:**
- Create on server: `~/stacks/sportiq/` (git clone)
- Create on server: `~/stacks/sportiq/.env` (owner pastes; agent must not cat it back)

**Interfaces:**
- Consumes: GitHub `https://github.com/Ninjabeam20/SportIQ-MCP` with Tasks 1–2 committed **and pushed** (if the clone would otherwise miss `docker-compose.yml`, scp the compose file instead — ask which)
- Produces: running container `sportiq` healthy on `apps`, listening on 8080 internally

- [ ] **Step 1: Re-check RAM**

```bash
ssh home-server 'awk "/MemAvailable/ {print}" /proc/meminfo'
```

Abort if available < 1500 MiB. Tell the owner which containers to stop; do not stop Jarvis or `edge` yourself.

- [ ] **Step 2: Clone (or pull) into `~/stacks/sportiq`**

If the directory does not exist:

```bash
ssh home-server 'git clone https://github.com/Ninjabeam20/SportIQ-MCP.git ~/stacks/sportiq'
```

If it exists:

```bash
ssh home-server 'cd ~/stacks/sportiq && git status && git pull --ff-only'
```

If Tasks 1–2 are only in the Mac worktree and not on GitHub, **do not clone an old main**. Either wait for a push or `scp` the needed files (`docker-compose.yml`, `Dockerfile`, `src/sportiq/core/request_limits.py`, `.env.example`). Prefer push + pull when the owner has said yes to push.

- [ ] **Step 3: Owner writes `.env` on the server**

The agent prints this template **with empty values only**, then waits. The owner SSHs and pastes real keys locally.

```bash
ssh home-server 'test -f ~/stacks/sportiq/.env || cp ~/stacks/sportiq/.env.example ~/stacks/sportiq/.env; chmod 600 ~/stacks/sportiq/.env'
```

Required non-secret lines the owner should end up with:

```
SPORTIQ_LOG_FORMAT=json
SPORTIQ_TRUST_CLOUDFLARE=1
DISKCACHE_DIR=/var/cache/sportiq
SPORTIQ_FOOTBALL_LIVE_ELO=1
SPORTIQ_ENABLE_NDTV=
SPORTIQ_ENABLE_CRICBUZZ=
REDIS_URL=
```

Keys policy (owner chooses, agent does not copy from `gcloud`):

- Default public host: leave `CRICAPI_KEY`, `THEODDS_KEY`, `APIFOOTBALL_KEY`, `RAPIDAPI_KEY` blank.
- Optional to match Cloud Run WC live data: `FOOTBALLDATA_KEY=` (owner pastes).
- Do not enable scrapers.

Agent must never run `gcloud run services describe` in a way that dumps env into the chat. If the owner wants to copy keys, they do it in their own terminal.

- [ ] **Step 4: Confirm `apps` network, then build and start**

```bash
ssh home-server 'docker network inspect apps >/dev/null && cd ~/stacks/sportiq && docker compose up -d --build'
```

Expected: image build succeeds; `Created` / `Started` `sportiq`.

- [ ] **Step 5: Wait for healthy, then internal curl**

```bash
ssh home-server 'docker compose -f ~/stacks/sportiq/docker-compose.yml ps'
ssh home-server 'docker logs sportiq --tail 50'
```

Then, from the server, MCP initialize over the `apps` network (not localhost on the host):

```bash
ssh home-server 'docker run --rm --network apps curlimages/curl -sS -X POST http://sportiq:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"}}}"'
```

Expected: JSON/SSE body containing `"serverInfo"` and `"name":"sportiq"`. If connection refused, the process is not bound to `0.0.0.0` (Dockerfile already does this — check logs). If 421/Host errors, DNS-rebinding protection is on — `server.py` already disables it for HTTP; do not "fix" by publishing ports.

---

### Task 6: Caddy live block + validate + reload (needs owner yes)

**Files:**
- Modify on server: `~/stacks/edge/Caddyfile` (one block only)
- Do not copy the entire intended file over the live file

**Interfaces:**
- Consumes: live Caddyfile from Task 0
- Produces: `http://sportiq.utkarshgupta.org` → `sportiq:8080` with `flush_interval -1`

- [ ] **Step 1: Diff live vs the one block you will keep**

Show the owner the exact before/after. If live still has `www` → `http://` apex, **leave it**. If live still routes `outfit` to a 502, **leave it**. As of 2026-08-30 the sportiq block **already exists** — the diff is “delete `header_up CF-Connecting-IP`”, not “append a new server block”.

- [ ] **Step 2: Edit live Caddyfile on the server**

Backup, then edit the existing `http://sportiq.utkarshgupta.org` block in place. Keep `flush_interval -1` and `header_up X-Forwarded-Proto https`. **Delete** `header_up CF-Connecting-IP {http.request.header.CF-Connecting-IP}`. Do not append a second sportiq block. Do not scp the full intended Caddyfile.

```bash
ssh home-server 'cp ~/stacks/edge/Caddyfile ~/stacks/edge/Caddyfile.bak-$(date +%Y%m%d-%H%M%S)'
```

- [ ] **Step 3: Validate before reload**

```bash
ssh home-server 'docker run --rm -v ~/stacks/edge/Caddyfile:/c:ro caddy:2-alpine caddy validate --config /c'
```

Expected: `Valid configuration`. If invalid, restore the `.bak-*` file and stop.

- [ ] **Step 4: Reload Caddy only**

```bash
ssh home-server 'cd ~/stacks/edge && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile'
```

- [ ] **Step 5: Curl via the edge network (still not public DNS)**

```bash
ssh home-server 'docker run --rm --network edge_edge curlimages/curl -sS -o /tmp/out -w "HTTP %{http_code}\n" \
  -H "Host: sportiq.utkarshgupta.org" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -X POST http://caddy:80/mcp \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"caddy-test\",\"version\":\"1.0\"}}}"'
```

Expected: HTTP 200 and `serverInfo` in the body.  
404 = missing Caddy block.  
502 = wrong container/port (`sportiq:8080`).  
Empty 200 = SSE buffering; confirm `flush_interval -1` and that you did not use Starlette `BaseHTTPMiddleware`.

Also confirm legacy path rewrite:

```bash
ssh home-server 'docker run --rm --network edge_edge curlimages/curl -sS -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Host: sportiq.utkarshgupta.org" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -X POST http://caddy:80/u/legacy-sponsor-key/mcp \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"legacy\",\"version\":\"1.0\"}}}"'
```

Expected: HTTP 200 (not 404).

---

### Task 7: Cloudflare hostname + prove the Dell (needs owner yes)

**Files:**
- Cloudflare Zero Trust dashboard only (no API token in this repo)

**Interfaces:**
- Consumes: existing tunnel named `home-server`, Caddy block from Task 6
- Produces: public hostname that **curl** can reach. Claude, ChatGPT, README, and `links.ts` **stay on Cloud Run**. This task does not flip anything.

The hostname becoming reachable is not the same as it being the public product URL. Two systems at once, one advertised URL.

- [ ] **Step 1: Add the published route (owner or agent with dashboard access)**

Cloudflare dashboard → Zero Trust → Networks → Tunnels → `home-server` → Public Hostname → Add:

- Subdomain: `sportiq`
- Domain: `utkarshgupta.org`
- Type: HTTP
- URL: `caddy:80`

Do **not** point at `sportiq:8080` (tunnel only sees Caddy on network `edge`).  
Do **not** create an Access application for this hostname.  
Do **not** create an A/AAAA to `192.168.29.66` or the IPv6 `2405:201:4:0009:21e:64ff:fed7:a9d3`.  
Do **not** add a router port-forward.

Optional defense in depth (same session, still no Access): Cloudflare WAF rate limit 60 req/min / IP on `sportiq.utkarshgupta.org`. Skip if the owner does not want to click WAF today.

- [ ] **Step 2: Initialize handshake from the Mac**

```bash
curl -sS -D - -X POST https://sportiq.utkarshgupta.org/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"mac","version":"1.0"}}}'
```

Expected: TLS from Cloudflare; HTTP 200; **non-empty** body containing `"serverInfo"` and `"name":"sportiq"`.  
Empty 200 = SSE buffering (`flush_interval -1` missing, or a global `encode` on `text/event-stream`).  
530/1033 = tunnel hostname missing. Wait 1–2 minutes for DNS, then recheck.  
A bare `curl -I` / GET returning 406 is healthy, not a routing failure.

Also send a bare `tools/list` on a **fresh** connection (stateless — no session id):

```bash
curl -sS -X POST https://sportiq.utkarshgupta.org/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Expected: 200 with the tool registry. A session-required error means the image predates `grok_changes13`; rebuild.

- [ ] **Step 3: Tool-call smoke (no provider key required)**

```bash
curl -sS -X POST https://sportiq.utkarshgupta.org/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"sportiq_health","arguments":{}}}'
```

Expected: 200 with the normal `{data, meta}` envelope — `cache_backend` `diskcache`, `cache_ok` true.

Optional second call: `football_get_groups`. Do not call live-odds tools if keys are blank (they should error with the normal envelope, not 500). Do **not** point Claude or ChatGPT at this URL yet — that is Task 8.

- [ ] **Step 4: 429s keyed on Cloudflare IP**

One Mac sending 61 initialize POSTs should overflow the 60/min per-client bucket. Do **not** run this against Cloud Run.

```bash
for i in $(seq 1 61); do
  curl -sS -o /dev/null -w "%{http_code}\n" -X POST https://sportiq.utkarshgupta.org/mcp \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"rl","version":"1.0"}}}'
done | sort | uniq -c
```

Expected: ~60 lines of `200` and at least one `429` with `Retry-After: 60` if you print headers on a rejected request. If the 61st is still 200, identity is not counting. If you 429 immediately, identity collapsed to Caddy's Docker IP (`header_up CF-Connecting-IP` is the usual cause — remove it). Wait a minute before any further prove curls.

- [ ] **Step 5: Confirm Jarvis did not become public**

```bash
curl -sI https://jarvis.utkarshgupta.org/ | head -n 20
```

Expected: still `302` to Cloudflare Access (or Access login), **not** 200 app HTML for anonymous.

- [ ] **Step 6: STOP. Report evidence. Do not flip.**

Paste the initialize body snippet, the health envelope, the 429 count, and Jarvis 302. Leave README / `links.ts` / SECURITY / Claude / ChatGPT on Cloud Run. Task 8 starts only when the owner replies `flip`.

---

### Task 8: Flip connectors and public docs (needs owner `flip`)

**Files:**
- Claude.ai / ChatGPT connector settings (owner)
- Modify: `README.md`, `SECURITY.md`, `website/src/config/links.ts` (`LINKS.hostedMcp`)
- Modify: `website/CLAUDE.md`, `PROJECT.md`, `CLAUDE.md`, `AGENTS.md`
- Modify: vault `Knowledge/Context/infrastructure.md`
- Modify: `docs/log.md`

Task 7 prove must already be green in this chat. Cloud Run **stays up** as rollback.

- [ ] **Step 1: Owner updates connectors**

- claude.ai → Settings → Connectors → custom connector URL `https://sportiq.utkarshgupta.org/mcp`
- ChatGPT → Developer Mode → connector URL the same
- Any leftover `/u/<key>/mcp` sponsor URLs: `https://sportiq.utkarshgupta.org/u/<key>/mcp` still rewrites

A curl 200 is not proof a connector works — connector auth/discovery has broken before while curl was green. Call `sportiq_health` (and optionally `football_get_groups`) from **both** Claude and ChatGPT.

- [ ] **Step 2: Swap the advertised URL**

Replace `https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp` with `https://sportiq.utkarshgupta.org/mcp` in README, SECURITY.md, and `website/src/config/links.ts`. Keep a one-line note that Cloud Run may exist until Task 9.

Update `CLAUDE.md` / `AGENTS.md` / `PROJECT.md` / `website/CLAUDE.md` so the **live** URL is the new hostname and Cloud Run is named only as rollback.

In vault `Knowledge/Context/infrastructure.md`, change `sportiq.` from "no DNS" / planned to **live** public MCP.

Append `docs/log.md` with a `release` line: hostname advertised, connectors flipped, Cloud Run still up as fallback.

The website needs a push for Vercel to pick `links.ts` up — push only if the owner asked.

- [ ] **Step 3: Confirm Cloud Run still works as rollback**

Do not delete it. Record: `https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp`. Keep it for a day or two (target ≥24h, prefer 48h). If credits expire sooner, the owner decides whether to shorten the soak — do not decide it for them.

**HARD STOP.** Task 9 is a different phrase.

---

### Task 9: GCP teardown to zero billing (needs `yes, delete GCP`)

**Files:**
- GCP: Cloud Scheduler `sportiq-keepwarm`, Cloud Run `sportiq-mcp`, Artifact Registry
- Modify after delete: `cloud.md` (historical, not rollback), GAPS/PROJECT/CLAUDE/AGENTS gotchas, `docs/log.md`

Do **not** teardown on the first public 200, and do not teardown in the same breath as Task 8. Claude **and** ChatGPT must have worked on the new URL. After Artifact Registry is gone there is no image to fail back to.

### What is actually costing money (check each, do not assume)

| Resource | Why it bills | Action |
|---|---|---|
| Cloud Scheduler `sportiq-keepwarm` (us-central1) | Pings `/mcp` on a schedule → wakes the service. **Main ongoing cost.** | Delete **first** |
| Cloud Run `sportiq-mcp` | Request/CPU time. Scales to zero once nothing pings it | Delete after soak |
| Artifact Registry `cloud-run-source-deploy` | Image storage past the 0.5 GB free tier; scipy image is ~1–1.5 GB and bills monthly forever | Delete after the service |
| Cloud Build | Unused once the pipeline is idle | Leave; verify no triggers |
| Cloud Logging | Drops to nothing once the service is gone | Leave |

- [ ] **Step 1: Paste, do not dry-run. Verify after each.**

```bash
# 1. Stop the keep-warm pings FIRST.
gcloud scheduler jobs list --location us-central1
gcloud scheduler jobs delete sportiq-keepwarm --location us-central1

# 2. Delete the service.
gcloud run services delete sportiq-mcp --region us-central1

# 3. Delete the stored images.
gcloud artifacts repositories list --location us-central1
gcloud artifacts repositories delete cloud-run-source-deploy --location us-central1

# 4. Confirm nothing is left running.
gcloud run services list --region us-central1
gcloud scheduler jobs list --location us-central1
```

- [ ] **Step 2: Zero-billing verification**

Two days after teardown, check the billing report for project `sportiq-mcp-prod` and confirm the running total stopped moving. Keep the ₹100/mo budget alert — it is alert-only. Project shutdown (`gcloud projects delete sportiq-mcp-prod`) is a **third** decision: do not do it unless the owner names the project and says yes.

- [ ] **Step 3: Docs in the same pass**

Mark `cloud.md` **historical** (the service no longer exists). Update GAPS/PROJECT/CLAUDE/AGENTS so they do not name Cloud Run as live failback. Append `docs/log.md`.

---

## Verify ladder (cheat sheet)

| Check | Command | Expect |
|---|---|---|
| SSH | `ssh home-server` | `ninjabeam20` |
| Edge | `docker compose -f ~/stacks/edge/docker-compose.yml ps` | caddy + cloudflared up |
| App | `docker compose -f ~/stacks/sportiq/docker-compose.yml ps` | `sportiq` up, no host ports |
| Internal | `curl` via `--network apps` to `http://sportiq:8080/mcp` initialize | `serverInfo` sportiq |
| Via Caddy | `curl` `--network edge_edge` `Host: sportiq.utkarshgupta.org` `http://caddy:80/mcp` POST initialize | HTTP 200 + body |
| Public prove | POST initialize + `tools/call sportiq_health` from Mac | TLS + non-empty `serverInfo` |
| 429 | 61 POSTs from one Mac | some `429` after ~60 `200` |
| Jarvis still private | `curl -sI https://jarvis.utkarshgupta.org/` | Access 302, not anonymous 200 |
| Advertised URL until Task 8 | README / `links.ts` / Claude | still Cloud Run `ey2eariulq` |
| 502 | wrong container/port | |
| 404 | missing Caddy block | |
| 530/1033 | missing tunnel hostname | |
| Empty 200 | SSE buffered | |

## Rollback

Valid only while Cloud Run still exists (before Task 9).

1. Point connectors back at `https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp`.
2. If Task 8 already swapped docs, revert README, SECURITY.md, `website/src/config/links.ts`, `website/CLAUDE.md`, `PROJECT.md`, `CLAUDE.md`, `AGENTS.md`, vault `infrastructure.md`. Rolling back the server while README still advertises a dead hostname reproduces the original dead-URL bug. Vercel needs a push for the revert.
3. Restore Caddy: `ssh home-server 'cp ~/stacks/edge/Caddyfile.bak-<timestamp> ~/stacks/edge/Caddyfile'` then reload.
4. Stop the app: `ssh home-server 'cd ~/stacks/sportiq && docker compose down'` (no `-v` unless the owner wants cache wiped).
5. Remove the Cloudflare published hostname `sportiq`.

After Task 9, recovery is rebuild from `cloud.md` (needs credits the owner may no longer have), not this list.

## Stateless — LANDED 2026-08-15, ships with this move

Full detail in `grok_changes13.md`. Summary for anyone verifying the deploy:

`src/sportiq/server.py` sets `mcp.settings.stateless_http = True` in the
`SPORTIQ_TRANSPORT=http` branch only. stdio (the uvx contract) is untouched. No
dependency change — the locked `mcp` 1.29.0 already supports it.

Consequences for the verify ladder below:

- **No `Mcp-Session-Id`.** The Task 7 note about capturing and echoing a session
  id for a one-shot smoke no longer applies. A bare `tools/list` POST on a fresh
  connection is now a complete end-to-end check at every layer.
- **`GET /mcp` is still 406** without MCP Accept headers — the Dockerfile
  HEALTHCHECK rule is unchanged. Verified against a live local server.
- **Legacy `/u/<key>/mcp` still rewrites and returns 200.** Verified.
- **Still one replica.** Stateless removed MCP session affinity, not the shared
  diskcache quota counters. `deploy.replicas` stays 1.
- **Rebuilds stop breaking connectors** — the reason it moved into scope.

Rollback is deleting one line and rebuilding. Nothing persists.

## Follow-up (separate plan, after this one is live)

- MCP Python SDK v2 / spec `2026-07-28` (`FastMCP` → `MCPServer`) — a real
  migration, gated by `mcp<2`. Its own plan, its own canary. Not this one.
- Optional Cloudflare WAF if not done in Task 7.
- Apply remaining `Caddyfile.intended` www/dead-route cleanup as its own owner-yes change.
- GCP project shutdown (`gcloud projects delete sportiq-mcp-prod`) only if the owner names the project and says yes — not part of Task 9.
