# Deploying SportIQ MCP to the cloud (Google Cloud Run)

This is the runbook to put SportIQ online at a public URL so it works on **any** AI
(claude.ai web, ChatGPT, phone apps) — not just desktop apps. The repo already has the
`Dockerfile` and HTTP support; you just run the steps below.

- **Why Cloud Run:** free tier, scales to zero ($0 when nobody's using it), enough memory.
- **What you get at the end:** a link like `https://sportiq-mcp-xxxx.a.run.app`, and your
  MCP endpoint is that link **+ `/mcp`**.

---

## PART 1 — Deploy (do this first)

### 1a. One-time setup

1. **Install the Google Cloud CLI** (Mac):
   ```
   brew install --cask google-cloud-sdk
   ```
   > If the brew cask fails (e.g. a Python virtualenv error on newer macOS), use the official
   > installer instead — it's self-contained and reliable:
   > ```
   > curl https://sdk.cloud.google.com | bash
   > ```
   > then restart your shell (or `source ~/.zshrc`) so `gcloud` is on your PATH.

2. **Log in:**
   ```
   gcloud auth login
   ```

3. **Create a project** (or use an existing one). Pick any unique id, e.g. `sportiq-mcp`:
   ```
   gcloud projects create sportiq-mcp-prod --name="SportIQ MCP"
   gcloud config set project sportiq-mcp-prod
   ```

4. **Enable billing.** Cloud Run *requires* a billing account on file, but you stay within
   the **free tier** for light use (it only charges if you exceed the free limits).
   - Go to: https://console.cloud.google.com/billing → link a billing account to the project.
   - Then set a safety budget alert (recommended): Billing → Budgets & alerts → create a
     budget of e.g. $5 so you're emailed if anything ever costs money.

5. **Turn on the needed services:**
   ```
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
   ```

### 1b. Deploy

From the repo root (`sportiq-mcp/`), run:

```
gcloud run deploy sportiq-mcp \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 1 \
  --port 8080
```

What this does:
- `--source .` → Google builds the `Dockerfile` for you in the cloud (no local Docker needed).
- `--region us-central1` → central US, a solid default for a **global** audience. (Cloud Run
  is regional, not multi-region; if most of your users are elsewhere, pick the closest region.)
- `--allow-unauthenticated` → makes the URL public so anyone can connect.
- `--memory 1Gi` → enough RAM for the World Cup bracket simulation. Bump to `2Gi` if it ever
  runs out of memory.
- `--max-instances 1` → required while request counters are process-local; raising it multiplies
  the effective global request limit and needs shared admission control first.

When it finishes it prints a **Service URL**. Your MCP endpoint = that URL **+ `/mcp`**.

> ⚠️ **DO NOT add your live-data API keys** (CricAPI, odds) here. A public URL with your keys
> means strangers can burn your daily quotas. Without keys, all your main tools (World Cup
> sims, F1 strategy, Dream11, predictions) still work — only live-score/odds tools stay off.

### 1c. Test it works

Replace `<URL>` with your Service URL:

```
curl -X POST <URL>/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

✅ Success = a response containing `"serverInfo":{"name":"sportiq"...}`.

---

## PART 2 — Connect it to AIs (after deploy)

Use your `<URL>/mcp` link.

- **claude.ai (web):** Settings → Connectors → **Add custom connector** → paste `<URL>/mcp`.
- **ChatGPT:** Settings → Connectors → turn on **Developer Mode** → **Create connector** →
  paste `<URL>/mcp`.
- **Cursor / VS Code (optional):** they can use the remote URL too, or keep using `uvx`.
- **Share it:** put the link in your README, posts, and directory listings so anyone can add it.

---

## PART 3 — Maintenance & later (as needed)

- **Push an update:** after changing code, just re-run the same `gcloud run deploy` command.
  It rebuilds and swaps in the new version with zero downtime.
- **See logs / debug:**
  ```
  gcloud run services logs read sportiq-mcp --region us-central1
  ```
- **Cold starts:** scale-to-zero means the *first* request after a quiet period is slow
  (~a few seconds) while it wakes up. To avoid that, add `--min-instances 1` to the deploy —
  but that keeps one instance always on and **leaves the free tier (small monthly cost)**.
  For a free setup, leave it at 0 and accept occasional cold starts.
- **Custom domain (optional):** Cloud Run → your service → "Custom domains" to map something
  like `mcp.yoursite.com`.
- **If the bracket sim crashes (out of memory):** redeploy with `--memory 2Gi`.
- **Cost check:** Cloud Run dashboard shows usage. With scale-to-zero + light traffic you
  should stay at $0; the budget alert from step 1a-4 is your safety net.

---

## Quick reference

| Thing | Value |
| --- | --- |
| Deploy command | `gcloud run deploy sportiq-mcp --source . --region us-central1 --allow-unauthenticated --memory 1Gi --cpu 1 --max-instances 1 --port 8080` |
| MCP endpoint | `<Service URL>/mcp` |
| Transport | streamable-HTTP (set by `SPORTIQ_TRANSPORT=http` in the Dockerfile) |
| Keep public, **no API keys** | avoids strangers burning your quotas |
| Update | re-run the deploy command |

---

## SportIQ Pro — hosted enforcement (V2a)

The hosted server can require a per-request **Pro key** for the 24 intelligence tools while
keeping the free data tools (and an optional flagship) open. It is driven by two env vars — no
code changes per deploy.

### Env vars

| Var | Effect |
| --- | --- |
| `SPORTIQ_VALID_KEYS` | Comma-separated set of valid Pro keys. **Set** → the gate validates the per-request key against this set (membership). **Unset** → presence check only (any non-blank key). On the host, set it to your issued key(s). |
| `SPORTIQ_FREE_TOOLS` | Comma-separated tool names kept FREE even though they are paid (e.g. `football_simulate_bracket`). Use it to keep one flagship open as a discovery funnel. Leave **unset** on PyPI so local installs stay fully gated. |

How a user supplies their key to the hosted server (claude.ai / ChatGPT have no key field):

- **URL path (primary, universal):** add the connector URL `…/u/<key>/mcp` with **No
  authentication**. Middleware reads the key from the path and rewrites it to `/mcp`.
- **`Authorization: Bearer <key>` header:** works on Claude Desktop / IDEs / the API.

### Deploy (canary pattern)

```bash
# 1. build the image at the current commit
gcloud builds submit --config cloudbuild.yaml --substitutions=_TAG=<git-sha> .

# 2. deploy as a NO-TRAFFIC canary, adding the Pro env vars (existing env preserved)
gcloud run deploy sportiq-mcp \
  --image us-central1-docker.pkg.dev/sportiq-mcp-prod/cloud-run-source-deploy/sportiq-mcp:<git-sha> \
  --region us-central1 --no-traffic --tag v2a --max-instances 1 \
  --update-env-vars SPORTIQ_VALID_KEYS=<key>,SPORTIQ_FREE_TOOLS=football_simulate_bracket

# 3. smoke-test the tagged canary URL (https://v2a---<service>.run.app/mcp): a gated tool must
#    return SUBSCRIPTION_REQUIRED with no key, the free tool must run, and …/u/<key>/mcp unlocks.

# 4. promote to 100%
gcloud run services update-traffic sportiq-mcp --region us-central1 --to-revisions=<new-rev>=100
```

> Always use `--update-env-vars` (adds/updates) — `--set-env-vars` REPLACES all env and would
> drop the existing ones (`FOOTBALLDATA_KEY`, `SPORTIQ_LOG_FORMAT`, `SPORTIQ_FOOTBALL_LIVE_ELO`).

### Rollback

```bash
gcloud run services update-traffic sportiq-mcp --region us-central1 --to-revisions=<previous-rev>=100
```

### Notes

- The key currently rides in the URL path, so it appears in Cloud Run HTTP access logs. Fine for a
  shared key; scrub before issuing per-user keys.
- Design + the V1→V2 boundary live in `docs/wiki/decisions/0011-pro-entitlement-gate.md`.
