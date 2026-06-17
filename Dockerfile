# Remote (HTTP) deployment of SportIQ MCP for Cloud Run / Fly.io / Render.
# Local install stays uvx/stdio; this image runs the same server over streamable-HTTP.
FROM python:3.13-slim

# coinor-cbc: the Dream11 ILP solver (PuLP COIN_CMD) needs a `cbc` binary on PATH.
RUN apt-get update \
    && apt-get install -y --no-install-recommends coinor-cbc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Dependency layer (cached) ---------------------------------------------
# Install all third-party deps against a STUB package so this heavy layer
# (scipy/numpy/pandas/fastf1, all compiled) is keyed only on pyproject.toml +
# README. Source-only edits no longer invalidate it — that was the old
# Dockerfile's bug: `COPY src` sat above `pip install`, so every code change
# forced a full from-scratch dependency reinstall.
COPY pyproject.toml README.md ./
RUN mkdir -p src/sportiq \
    && : > src/sportiq/__init__.py \
    && pip install --no-cache-dir ".[f1]"

# --- Source layer (fast) ----------------------------------------------------
# Copy the real source and reinstall ONLY the project package (--no-deps), so
# this step never touches the cached dependency layer above.
COPY src ./src
RUN pip install --no-cache-dir --no-deps --force-reinstall .

# Serve over HTTP. Cloud Run/Fly/Render inject $PORT; default to 8080 locally.
ENV SPORTIQ_TRANSPORT=http \
    PORT=8080
EXPOSE 8080

# MCP endpoint is served at /mcp
CMD ["python", "-m", "sportiq.server"]
