"""S.6a — Same-host redirect enforcement and response-size ceiling."""

import httpx
import pytest
import respx

from sportiq.core.http import close_client, get_json


@pytest.fixture(autouse=True)
async def reset_client():
    """Reset the global HTTP client before and after each test."""
    await close_client()
    yield
    await close_client()


@respx.mock
async def test_same_host_redirect_is_followed():
    """A redirect to the same host is followed transparently."""
    respx.get("https://api.example.com/v1/data").mock(
        return_value=httpx.Response(301, headers={"location": "https://api.example.com/v2/data"})
    )
    respx.get("https://api.example.com/v2/data").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    result = await get_json("https://api.example.com/v1/data")
    assert result == {"ok": True}


@respx.mock
async def test_cross_host_redirect_is_blocked():
    """A redirect to a different host raises HTTPStatusError."""
    respx.get("https://api.example.com/v1/data").mock(
        return_value=httpx.Response(301, headers={"location": "https://attacker.evil.com/steal"})
    )
    with pytest.raises(httpx.HTTPStatusError, match="Cross-host redirect blocked"):
        await get_json("https://api.example.com/v1/data")


@respx.mock
async def test_response_too_large_is_rejected():
    """A response over 10 MB raises ValueError."""
    big_body = b"x" * (10 * 1024 * 1024 + 1)
    respx.get("https://api.example.com/v1/data").mock(
        return_value=httpx.Response(200, content=big_body)
    )
    with pytest.raises(ValueError, match="Response too large"):
        await get_json("https://api.example.com/v1/data")


@respx.mock
async def test_normal_response_is_returned():
    """A normal JSON response is returned unchanged."""
    respx.get("https://api.example.com/v1/data").mock(
        return_value=httpx.Response(200, json={"matches": []})
    )
    result = await get_json("https://api.example.com/v1/data")
    assert result == {"matches": []}


@respx.mock
async def test_multiple_same_host_redirects():
    """Multiple same-host redirects are followed in sequence."""
    respx.get("https://api.example.com/v1/data").mock(
        return_value=httpx.Response(301, headers={"location": "https://api.example.com/v2/data"})
    )
    respx.get("https://api.example.com/v2/data").mock(
        return_value=httpx.Response(302, headers={"location": "https://api.example.com/v3/data"})
    )
    respx.get("https://api.example.com/v3/data").mock(
        return_value=httpx.Response(200, json={"final": True})
    )
    result = await get_json("https://api.example.com/v1/data")
    assert result == {"final": True}


@respx.mock
async def test_cross_host_redirect_blocked_after_same_host():
    """Cross-host redirect is blocked even after one valid same-host redirect."""
    respx.get("https://api.example.com/v1/data").mock(
        return_value=httpx.Response(301, headers={"location": "https://api.example.com/v2/data"})
    )
    respx.get("https://api.example.com/v2/data").mock(
        return_value=httpx.Response(301, headers={"location": "https://attacker.evil.com/pwned"})
    )
    with pytest.raises(httpx.HTTPStatusError, match="Cross-host redirect blocked"):
        await get_json("https://api.example.com/v1/data")


@respx.mock
async def test_response_at_size_limit_is_accepted():
    """A response exactly at 10 MB is accepted (size check passes)."""
    # Create a 10 MB JSON response (valid JSON within size limit)
    json_str = '{"data": "' + "x" * (10 * 1024 * 1024 - 20) + '"}'
    body = json_str.encode("utf-8")
    assert len(body) <= 10 * 1024 * 1024
    respx.get("https://api.example.com/v1/data").mock(
        return_value=httpx.Response(200, content=body)
    )
    result = await get_json("https://api.example.com/v1/data")
    assert "data" in result


@respx.mock
async def test_redirect_with_missing_location_header():
    """A redirect without a Location header raises HTTPStatusError."""
    respx.get("https://api.example.com/v1/data").mock(
        return_value=httpx.Response(301)  # No Location header
    )
    with pytest.raises(httpx.HTTPStatusError, match="Redirect response has no Location header"):
        await get_json("https://api.example.com/v1/data")
