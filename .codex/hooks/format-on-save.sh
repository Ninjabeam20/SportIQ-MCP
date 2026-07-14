#!/usr/bin/env bash
# Runs ruff format + ruff check --fix on the file(s) the agent just wrote/edited.
# Best-effort: silent on success, prints nothing destructive on failure.

set -u

# Read hook input from stdin (Claude Code passes a JSON blob).
input="$(cat)"

# Extract file path with a tiny python helper — no jq dependency.
if ! file_path="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    path = data["tool_input"]["file_path"]
    if not isinstance(path, str) or not path.strip():
        raise ValueError("missing file_path")
except Exception:
    raise SystemExit(2)
print(path)
')"; then
  # Formatting is a convenience hook: an unknown event shape is not applicable.
  exit 0
fi

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
