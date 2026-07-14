"""Pure-ASGI admission controls for the hosted streamable-HTTP endpoint."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import time

from sportiq.core.cache import get_cache


def _header(scope: dict, name: bytes) -> str:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1")
    return ""


def _client_identity(scope: dict, *, trust_forwarded: bool) -> str:
    """Return the rate-limit identity without trusting caller-supplied XFF locally."""
    if trust_forwarded:
        forwarded = _header(scope, b"x-forwarded-for")
        candidate = forwarded.split(",", 1)[0].strip()
        if candidate:
            try:
                return str(ipaddress.ip_address(candidate))
            except ValueError:
                pass

    client = scope.get("client")
    if isinstance(client, (tuple, list)) and client:
        return str(client[0])
    return "unknown"


async def _json_response(
    send, status: int, message: str, retry_after: int | None = None
) -> None:
    body = json.dumps({"error": message}, separators=(",", ":")).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]
    if retry_after is not None:
        headers.append((b"retry-after", str(retry_after).encode()))
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class RequestLimitMiddleware:
    """Bound and rate-limit POST bodies reaching the MCP HTTP endpoint."""

    def __init__(
        self,
        app,
        *,
        max_body_bytes: int,
        per_client_per_minute: int,
        global_per_minute: int,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.per_client_per_minute = per_client_per_minute
        self.global_per_minute = global_per_minute
        self.trust_forwarded = bool(os.getenv("K_SERVICE"))

    async def __call__(self, scope, receive, send) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path", "").rstrip("/") != "/mcp"
        ):
            await self.app(scope, receive, send)
            return

        content_length = _header(scope, b"content-length")
        try:
            declared_length = int(content_length) if content_length else None
        except ValueError:
            declared_length = None
        if declared_length is not None and declared_length > self.max_body_bytes:
            await _json_response(send, 413, "request body too large")
            return

        cache = get_cache()
        window = int(time.time()) // 60
        identity = _client_identity(scope, trust_forwarded=self.trust_forwarded)
        identity_hash = hashlib.blake2s(identity.encode(), digest_size=8).hexdigest()
        client_count = await cache.incr_counter(
            f"sportiq:http:client:{window}:{identity_hash}", ttl_seconds=120
        )
        if client_count > self.per_client_per_minute:
            await _json_response(send, 429, "client rate limit exceeded", retry_after=60)
            return

        global_count = await cache.incr_counter(
            f"sportiq:http:global:{window}", ttl_seconds=120
        )
        if global_count > self.global_per_minute:
            await _json_response(send, 429, "global rate limit exceeded", retry_after=60)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message.get("type") == "http.disconnect":
                return
            if message.get("type") != "http.request":
                await _json_response(send, 400, "incomplete request body")
                return
            chunk = message.get("body", b"")
            remaining = self.max_body_bytes + 1 - len(body)
            body.extend(chunk[:remaining])
            if len(body) > self.max_body_bytes or len(chunk) > remaining:
                await _json_response(send, 413, "request body too large")
                return
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay_receive() -> dict:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {
                    "type": "http.request",
                    "body": bytes(body),
                    "more_body": False,
                }
            return await receive()

        await self.app(scope, replay_receive, send)
