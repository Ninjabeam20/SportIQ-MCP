"""Shared async HTTP client with tenacity-based retry.

Adapters use `get_client()` rather than constructing httpx.AsyncClient directly,
so we have a single choke point for headers, timeouts, and retry policy.
"""

from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": "sportiq-mcp/0.1"},
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def get_json(url: str, **kwargs) -> dict:
    """GET a URL and return parsed JSON. Retries on transport errors and 5xx."""
    client = get_client()
    response = await client.get(url, **kwargs)
    response.raise_for_status()
    return response.json()
