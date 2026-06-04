"""Shared MCP tool annotations.

Every SportIQ tool is a read: it fetches/derives sports data and never mutates
upstream state. The MCP annotation hints communicate that to clients (per
mcp-builder rubric). One shared set covers all 44 tools:

- readOnlyHint   True  — no tool modifies its environment.
- destructiveHint False — nothing is destroyed; pairs with readOnly.
- idempotentHint True  — repeated calls have no *additional* effect (no side
  effects). Monte-Carlo tools may return different samples run-to-run, but that
  is output variance, not state change — still idempotent in the MCP sense.
- openWorldHint  True  — tools read from / depend on external upstreams
  (CricAPI, OpenF1, Jolpica, The Odds API, API-Football) and the static seeds
  that stand in for them; freshness is open-world.
"""

from __future__ import annotations

READ_ONLY: dict[str, bool] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}
