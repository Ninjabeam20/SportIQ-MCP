#!/usr/bin/env bash
# Blocks destructive shell commands before they reach Bash.
# Exit 2 → tool call is blocked; stderr is shown to the model.

set -u

input="$(cat || true)"
cmd="$(python3 - <<'PY' <<<"$input" 2>/dev/null || true
import json, sys
try:
    data = json.loads(sys.stdin.read())
    print(data.get("tool_input", {}).get("command", ""))
except Exception:
    pass
PY
)"

# Patterns we never want executed without explicit user override.
deny_patterns=(
  'rm -rf /'
  'rm -rf ~'
  'rm -rf \*'
  'sudo rm'
  ':\(\)\{ :|:& \};:'        # fork bomb
  'mkfs'
  'dd if=.*of=/dev/'
  'FLUSHALL'
  'flushall'
  'DROP DATABASE'
  'git push --force'
  'git push -f '
  'git reset --hard origin'
)

for pat in "${deny_patterns[@]}"; do
  if echo "$cmd" | grep -E -q "$pat"; then
    echo "Blocked by .claude/hooks/block-dangerous-bash.sh: matched pattern '$pat'." >&2
    echo "If this is intentional, run it yourself or remove the pattern from the hook." >&2
    exit 2
  fi
done

exit 0
