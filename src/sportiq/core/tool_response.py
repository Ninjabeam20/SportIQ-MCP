from typing import Any

from sportiq.core.errors import ErrorCode


def tool_response(result: Any) -> dict:
    """Wrap a FallbackResult-shaped value into the {data, meta} envelope.

    Accepts either a FallbackResult instance or a plain value (in which case
    `meta` is minimal).
    """
    if hasattr(result, "value") and hasattr(result, "source"):
        return {
            "data": result.value,
            "meta": {
                "source": result.source,
                "is_stale": getattr(result, "is_stale", False),
                "data_age_seconds": getattr(result, "data_age_seconds", 0),
                "fallback_used": getattr(result, "fallback_used", False),
                "duration_ms": getattr(result, "duration_ms", 0),
            },
        }
    return {"data": result, "meta": {"source": "inline", "is_stale": False}}


def error_envelope(
    code: ErrorCode,
    message: str,
    sources_tried: list[dict] | None = None,
    retry_after_seconds: int | None = None,
    suggestion: str | None = None,
) -> dict:
    """Build a uniform error envelope per .claude/rules/error-envelope.md."""
    envelope: dict = {"error": {"code": code, "message": message}}
    if sources_tried:
        envelope["error"]["sources_tried"] = sources_tried
    if retry_after_seconds is not None:
        envelope["error"]["retry_after_seconds"] = retry_after_seconds
    if suggestion:
        envelope["error"]["suggestion"] = suggestion
    return envelope
