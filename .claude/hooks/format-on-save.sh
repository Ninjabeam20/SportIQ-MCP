#!/usr/bin/env bash
# Runs ruff format + ruff check --fix on the file(s) the agent just wrote/edited.
# Best-effort: silent on success, prints nothing destructive on failure.

set -u

# Read hook input from stdin (Claude Code passes a JSON blob).
input="$(cat || true)"

# Extract file path with a tiny python helper — no jq dependency.
file_path="$(python3 - <<'PY' <<<"$input" 2>/dev/null || true
import json, sys
try:
    data = json.loads(sys.stdin.read())
    print(data.get("tool_input", {}).get("file_path", ""))
except Exception:
    pass
PY
)"

# Only act on Python files inside this repo.
case "$file_path" in
  *.py)
    if command -v uv >/dev/null 2>&1; then
      uv run ruff format "$file_path" >/dev/null 2>&1 || true
      uv run ruff check --fix "$file_path" >/dev/null 2>&1 || true
    fi
    ;;
esac

exit 0
