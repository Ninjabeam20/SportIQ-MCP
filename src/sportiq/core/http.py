"""Shared async HTTP client with tenacity-based retry.

Adapters use `get_client()` rather than constructing httpx.AsyncClient directly,
so we have a single choke point for headers, timeouts, and retry policy.
"""

from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

_client: httpx.AsyncClient | None = None


def _should_retry(exc: BaseException) -> bool:
    """Retry transport errors and 5xx only. 4xx (401/403/404/429) fail fast.

    Retrying a bad-auth or quota (429) response would burn 3x the upstream
    quota for a guaranteed-failure call; only server-side faults are transient.
    """
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


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
    retry=retry_if_exception(_should_retry),
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
