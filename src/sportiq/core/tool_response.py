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


def staleness_meta(*results: Any) -> dict:
    """Aggregate freshness signals across the chains a tool read.

    INTEL tools compose several chains; any one of them can serve stale data.
    Per .claude/rules/fallback-contract.md the worst-case staleness MUST be
    surfaced in ``meta`` rather than swallowed. Returns the fields to splat into
    a hand-built ``meta`` dict::

        {"is_stale": any(...), "data_age_seconds": max(...), "fallback_used": any(...)}

    Args:
        *results: FallbackResult instances (any object exposing is_stale /
            data_age_seconds / fallback_used).
    """
    return {
        "is_stale": any(getattr(r, "is_stale", False) for r in results),
        "data_age_seconds": max(
            (getattr(r, "data_age_seconds", 0) for r in results), default=0
        ),
        "fallback_used": any(getattr(r, "fallback_used", False) for r in results),
    }


_MAX_LIST_ITEMS = 200
_MAX_STRING_LEN = 500


def truncate_payload(data: dict, list_key: str, max_items: int = _MAX_LIST_ITEMS) -> tuple[dict, bool]:
    """Truncate an oversized list in `data[list_key]` in-place.

    Returns (data, was_truncated). Tools should set meta.truncated=True when was_truncated.
    """
    lst = data.get(list_key)
    if isinstance(lst, list) and len(lst) > max_items:
        data[list_key] = lst[:max_items]
        return data, True
    return data, False


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
