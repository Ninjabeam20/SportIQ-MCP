"""Shared async HTTP client with tenacity-based retry.

Adapters use `get_client()` rather than constructing httpx.AsyncClient directly,
so we have a single choke point for headers, timeouts, and retry policy.

S.6a hardening: same-host-only redirects + 10 MB response ceiling.
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

_client: httpx.AsyncClient | None = None
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB


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


def _should_retry_burst(exc: BaseException) -> bool:
    """Like ``_should_retry`` but ALSO retries 429.

    Only for sources with **no daily quota** that rate-limit short bursts
    (OpenF1). There, a 429 is a transient "slow down", not a quota wall, so
    backing off and retrying is correct and burns no billable quota. NEVER use
    this for quota-capped APIs (CricAPI, The Odds API, API-Football) — see
    .claude/rules/api-budgets.md.
    """
    if _should_retry(exc):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429
    return False


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,  # same-host redirects only, enforced in get_json
            headers={"User-Agent": "sportiq-mcp/0.1"},
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _fetch_json_once(url: str, **kwargs) -> dict:
    """Single GET with same-host-redirect + 10 MB-ceiling enforcement.

    The retry policy lives on the public wrappers below; this is one attempt.
    """
    client = get_client()
    original_host = urlparse(url).netloc
    response = await client.get(url, **kwargs)

    hops = 0
    while response.is_redirect and hops < 5:
        location = response.headers.get("location", "")
        if not location:
            raise httpx.HTTPStatusError(
                "Redirect response has no Location header",
                request=response.request,
                response=response,
            )
        redirect_host = urlparse(location).netloc
        if redirect_host and redirect_host != original_host:
            raise httpx.HTTPStatusError(
                f"Cross-host redirect blocked: {original_host!r} -> {redirect_host!r}",
                request=response.request,
                response=response,
            )
        response = await client.get(location, **kwargs)
        hops += 1

    response.raise_for_status()
    if len(response.content) > _MAX_RESPONSE_BYTES:
        raise ValueError(f"Response too large ({len(response.content)} bytes); rejecting.")
    return response.json()


@retry(
    retry=retry_if_exception(_should_retry),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def get_json(url: str, **kwargs) -> dict:
    """GET a URL and return parsed JSON. Retries on transport errors and 5xx.

    Does NOT retry 429 (quota protection). Rejects cross-host redirects and
    responses over 10 MB.
    """
    return await _fetch_json_once(url, **kwargs)


@retry(
    retry=retry_if_exception(_should_retry_burst),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
    stop=stop_after_attempt(4),
    reraise=True,
)
async def get_json_burst(url: str, **kwargs) -> dict:
    """GET for no-quota, burst-rate-limited sources (OpenF1).

    Identical to ``get_json`` but ALSO retries 429 with exponential backoff —
    OpenF1 throttles short bursts but has no daily cap, so a brief back-off
    clears the limit without consuming any billable quota. Do not use for
    quota-capped APIs.
    """
    return await _fetch_json_once(url, **kwargs)
