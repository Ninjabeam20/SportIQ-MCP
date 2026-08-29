# Remote (HTTP) deployment of SportIQ MCP for Cloud Run rollback or
# home-server Compose (Dell, network `apps`, no published host ports).
# Local install stays uvx/stdio; this image runs the same server over streamable-HTTP.
FROM python:3.13-slim

# coinor-cbc: the Dream11 ILP solver (PuLP COIN_CMD) needs a `cbc` binary on PATH.
RUN apt-get update \
    && apt-get install -y --no-install-recommends coinor-cbc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# --- Dependency layer (cached) ---------------------------------------------
# Install all third-party deps against a STUB package so this heavy layer
# (scipy/numpy/pandas/fastf1, all compiled) is keyed on pyproject.toml +
# uv.lock + README. Source-only edits no longer invalidate it. --frozen pins
# the image to the same versions CI tested; do not revert to unpinned pip.
COPY pyproject.toml uv.lock README.md ./
RUN mkdir -p src/sportiq \
    && : > src/sportiq/__init__.py \
    && uv pip install --system --frozen ".[f1]"

# --- Source layer (fast) ----------------------------------------------------
# Copy the real source and reinstall ONLY the project package (--no-deps), so
# this step never touches the cached dependency layer above.
COPY src ./src
RUN uv pip install --system --no-deps --reinstall .

# Serve over HTTP. Cloud Run/Fly/Render inject $PORT; default to 8080 locally.
ENV SPORTIQ_TRANSPORT=http \
    PORT=8080
EXPOSE 8080

# MCP endpoint is served at /mcp
# GET /mcp is 406 without MCP Accept headers; that still means the process is up.
# Localhost liveness only — not a keep-warm ping. Do not add a scheduler for this.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.error, urllib.request\nreq = urllib.request.Request('http://127.0.0.1:8080/mcp')\ntry:\n    urllib.request.urlopen(req, timeout=4)\n    sys.exit(0)\nexcept urllib.error.HTTPError as e:\n    sys.exit(0 if e.code in (400, 405, 406) else 1)\nexcept Exception:\n    sys.exit(1)"]
CMD ["python", "-m", "sportiq.server"]
