# Remote (HTTP) deployment of SportIQ MCP for Cloud Run / Fly.io / Render.
# Local install stays uvx/stdio; this image runs the same server over streamable-HTTP.
FROM python:3.13-slim

# coinor-cbc: the Dream11 ILP solver (PuLP COIN_CMD) needs a `cbc` binary on PATH.
RUN apt-get update \
    && apt-get install -y --no-install-recommends coinor-cbc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the package from source so the image includes the streamable-HTTP entrypoint
# (and the F1 extra). Build context is the repo root.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[f1]"

# Serve over HTTP. Cloud Run/Fly/Render inject $PORT; default to 8080 locally.
ENV SPORTIQ_TRANSPORT=http \
    PORT=8080
EXPOSE 8080

# MCP endpoint is served at /mcp
CMD ["python", "-m", "sportiq.server"]
