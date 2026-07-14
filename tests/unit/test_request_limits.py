from __future__ import annotations

import asyncio
import json

from sse_starlette import EventSourceResponse
from starlette.requests import Request

from sportiq.core.request_limits import RequestLimitMiddleware, _client_identity


class _RecordingApp:
    def __init__(self) -> None:
        self.calls = 0
        self.bodies: list[bytes] = []

    async def __call__(self, scope, receive, send) -> None:
        self.calls += 1
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        self.bodies.append(bytes(body))
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


class _StreamingApp:
    def __init__(self) -> None:
        self.body = b""

    async def __call__(self, scope, receive, send) -> None:
        request = Request(scope, receive)
        self.body = await request.body()

        async def events():
            for index in range(3):
                await asyncio.sleep(0)
                yield {"data": f"chunk-{index}"}

        await EventSourceResponse(events(), ping=None)(scope, receive, send)


async def _request(
    middleware,
    *,
    path: str = "/mcp",
    method: str = "POST",
    chunks: tuple[bytes, ...] = (b"{}",),
    headers: list[tuple[bytes, bytes]] | None = None,
    client: tuple[str, int] = ("192.0.2.10", 1234),
    disconnect_after_body: bool = True,
) -> list[dict]:
    messages = [
        {
            "type": "http.request",
            "body": chunk,
            "more_body": index < len(chunks) - 1,
        }
        for index, chunk in enumerate(chunks)
    ]

    async def receive() -> dict:
        if messages:
            return messages.pop(0)
        if disconnect_after_body:
            return {"type": "http.disconnect"}
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    sent: list[dict] = []

    async def send(message: dict) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "path": path,
        "method": method,
        "headers": headers or [],
        "client": client,
    }
    await middleware(scope, receive, send)
    return sent


def _status(messages: list[dict]) -> int:
    return next(m["status"] for m in messages if m["type"] == "http.response.start")


def _headers(messages: list[dict]) -> dict[bytes, bytes]:
    start = next(m for m in messages if m["type"] == "http.response.start")
    return dict(start["headers"])


def _middleware(app, *, body=8, client=2, global_limit=10):
    return RequestLimitMiddleware(
        app,
        max_body_bytes=body,
        per_client_per_minute=client,
        global_per_minute=global_limit,
    )


async def test_request_limit_rejects_declared_oversize_before_downstream():
    app = _RecordingApp()
    sent = await _request(
        _middleware(app),
        chunks=(b"ignored",),
        headers=[(b"content-length", b"9")],
    )

    assert _status(sent) == 413
    assert app.calls == 0


async def test_request_limit_rejects_chunked_oversize_at_one_byte_over_limit():
    app = _RecordingApp()
    sent = await _request(_middleware(app), chunks=(b"1234", b"56789"))

    assert _status(sent) == 413
    assert app.calls == 0


async def test_request_limit_replays_accepted_body_byte_for_byte():
    app = _RecordingApp()
    sent = await _request(_middleware(app), chunks=(b"abc", b"def"))

    assert _status(sent) == 200
    assert app.bodies == [b"abcdef"]


async def test_request_limit_preserves_sse_stream_after_body_replay():
    app = _StreamingApp()

    sent = await asyncio.wait_for(
        _request(
            _middleware(app),
            disconnect_after_body=False,
        ),
        timeout=1,
    )

    body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    assert app.body == b"{}"
    assert _status(sent) == 200
    assert all(f"data: chunk-{index}".encode() in body for index in range(3))


async def test_request_limit_returns_silently_on_mid_body_disconnect():
    app = _RecordingApp()
    middleware = _middleware(app)
    messages = [
        {"type": "http.request", "body": b"partial", "more_body": True},
        {"type": "http.disconnect"},
    ]

    async def receive() -> dict:
        return messages.pop(0)

    sent: list[dict] = []

    async def send(message: dict) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "path": "/mcp",
        "method": "POST",
        "headers": [],
        "client": ("192.0.2.10", 1234),
    }
    await middleware(scope, receive, send)

    assert app.calls == 0
    assert sent == []


async def test_request_limit_returns_429_with_retry_after_per_client():
    app = _RecordingApp()
    middleware = _middleware(app)

    assert _status(await _request(middleware)) == 200
    assert _status(await _request(middleware)) == 200
    rejected = await _request(middleware)

    assert _status(rejected) == 429
    assert _headers(rejected)[b"retry-after"] == b"60"
    assert json.loads(rejected[-1]["body"])["error"] == "client rate limit exceeded"
    assert app.calls == 2


async def test_request_limit_returns_429_at_global_ceiling_across_clients():
    app = _RecordingApp()
    middleware = _middleware(app, client=10, global_limit=3)

    for index in range(3):
        sent = await _request(middleware, client=(f"192.0.2.{index + 1}", 1234))
        assert _status(sent) == 200
    rejected = await _request(middleware, client=("192.0.2.99", 1234))

    assert _status(rejected) == 429
    assert _headers(rejected)[b"retry-after"] == b"60"
    assert app.calls == 3


def test_request_limit_ignores_xff_outside_cloud_run():
    scope = {
        "headers": [(b"x-forwarded-for", b"203.0.113.7")],
        "client": ("192.0.2.10", 1234),
    }
    assert _client_identity(scope, trust_forwarded=False) == "192.0.2.10"


def test_request_limit_uses_valid_leftmost_xff_on_cloud_run():
    scope = {
        "headers": [(b"x-forwarded-for", b"203.0.113.7, 198.51.100.2")],
        "client": ("192.0.2.10", 1234),
    }
    assert _client_identity(scope, trust_forwarded=True) == "203.0.113.7"
    scope["headers"] = [(b"x-forwarded-for", b"not-an-ip, 198.51.100.2")]
    assert _client_identity(scope, trust_forwarded=True) == "192.0.2.10"


async def test_request_limit_passes_get_and_non_mcp_requests_unchanged():
    app = _RecordingApp()
    middleware = _middleware(app, client=1, global_limit=1)

    assert _status(await _request(middleware, method="GET", chunks=(b"get",))) == 200
    assert _status(await _request(middleware, path="/health", chunks=(b"health",))) == 200
    assert app.bodies == [b"get", b"health"]
