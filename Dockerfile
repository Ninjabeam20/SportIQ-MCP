# Remote (HTTP) deployment of SportIQ MCP for home-server Compose
# (Dell, network `apps`, no published host ports). Cloud Run is gone.
# Local install stays uvx/stdio; this image runs the same server over streamable-HTTP.
FROM python:3.13-slim

# coinor-cbc: the Dream11 ILP solver (PuLP COIN_CMD) needs a `cbc` binary on PATH.
RUN apt-get update \
    && apt-get install -y --no-install-recommends coinor-cbc \
    && rm -rf /var/lib/apt/lists/*

# Pin uv. `:latest` dropped `uv pip install --frozen` (never a pip-interface
# flag; `uv sync`/`uv export` own --frozen). Pin so Dell Compose builds do
# not float onto a breaking CLI.
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /bin/uv

WORKDIR /app

# --- Dependency layer (cached) ---------------------------------------------
# Install all third-party deps against a STUB package so this heavy layer
# (scipy/numpy, compiled) is keyed on pyproject.toml + uv.lock + README.
# Source-only edits no longer invalidate it. --frozen pins the image to the
# same versions CI tested; do not revert to unpinned pip. The hosted image
# omits the f1 extra (fastf1/pandas/matplotlib/pillow): the FastF1 fallbacks
# report "not installed" and the chains walk past them (ADR-0014).
COPY pyproject.toml uv.lock README.md ./
RUN mkdir -p src/sportiq \
    && : > src/sportiq/__init__.py \
    && uv export --frozen --no-dev --no-emit-project -o /tmp/reqs.txt \
    && uv pip install --system -r /tmp/reqs.txt

# --- Source layer (fast) ----------------------------------------------------
# Copy the real source and reinstall ONLY the project package (--no-deps), so
# this step never touches the cached dependency layer above.
COPY src ./src
RUN uv pip install --system --no-deps --reinstall .

# Serve over HTTP. Compose sets PORT=8080; default to 8080 locally (behavior unchanged).
ENV SPORTIQ_TRANSPORT=http \
    PORT=8080
EXPOSE 8080

# MCP endpoint is served at /mcp
# GET /healthz is a liveness route that returns 200 "ok" without touching the cache,
# chains or network (probing /mcp ran the FastMCP lifespan on every check).
# Localhost liveness only — not a keep-warm ping. Do not add a scheduler for this.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request\ntry:\n    with urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4) as r:\n        sys.exit(0 if r.status == 200 else 1)\nexcept Exception:\n    sys.exit(1)"]
CMD ["python", "-m", "sportiq.server"]
