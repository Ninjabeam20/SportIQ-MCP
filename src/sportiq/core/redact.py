"""Redact secrets from strings before they reach the error envelope or logs.

CricAPI and The Odds API carry their API key as a URL **query param**
(``apikey=`` / ``apiKey=``). An ``httpx`` exception string embeds the full
request URL, so ``str(exc)`` leaks the key when it is stored in
``FallbackChain.attempts`` (→ the error envelope's ``sources_tried``) or written
to a log. ``scrub`` is the single choke point: call it wherever an exception,
URL, or header dict becomes a stored/emitted string.

Redaction is twofold:
  1. **Structural** — query params whose *name* looks secret, plus auth headers.
  2. **Value-based** — the literal credential values from ``settings``, so a key
     is caught wherever it appears even if the surrounding text is unusual.
"""

from __future__ import annotations

import re

REDACTED = "***"

# Query params whose NAME is a known secret. Matched positionally right after
# `?`/`&` so non-secret params that merely *contain* "key" (e.g. OpenF1's
# `session_key`) are left intact.
_QUERY_SECRET = re.compile(
    r"(?i)([?&](?:api[_-]?key|access[_-]?token|auth[_-]?token|token|secret|password|signature|sig|key)=)"
    r"([^&\s#'\"<>]+)"
)

# Authorization / api-key style headers rendered into a string or repr.
_HEADER_SECRET = re.compile(
    r"(?i)((?:authorization|x-rapidapi-key|x-api-key|api-key)['\"]?\s*[:=]\s*['\"]?)"
    r"(?:bearer\s+)?([^\s,'\"}\]]+)"
)


def scrub(text: str) -> str:
    """Return *text* with secret query-param values, auth headers, and known
    credential values redacted. Safe on any string; returns it unchanged when
    no secret is present.
    """
    if not text:
        return text
    out = _QUERY_SECRET.sub(rf"\1{REDACTED}", text)
    out = _HEADER_SECRET.sub(rf"\1{REDACTED}", out)
    return _scrub_known_values(out)


def _scrub_known_values(text: str) -> str:
    """Replace the literal values of every configured credential.

    Imported lazily so this module has no import-time dependency on settings
    (and so test monkeypatches of ``settings`` are honoured at call time).
    """
    from sportiq.config import settings

    for value in (
        settings.cricapi_key,
        settings.apifootball_key,
        settings.footballdata_key,
        settings.rapidapi_key,
        settings.theodds_key,
    ):
        if value:
            text = text.replace(value, REDACTED)
    return text
