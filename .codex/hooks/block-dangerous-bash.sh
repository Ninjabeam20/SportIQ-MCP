#!/usr/bin/env bash
# Blocks destructive shell commands before they reach Bash.
# Exit 2 → tool call is blocked; stderr is shown to the model.

set -u

input="$(cat)"
if ! cmd="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    command = data["tool_input"]["command"]
    if not isinstance(command, str) or not command.strip():
        raise ValueError("missing command")
except Exception as exc:
    print(f"invalid hook input: {exc}", file=sys.stderr)
    raise SystemExit(2)
print(" ".join(command.split()))
')"; then
  exit 2
fi

# Patterns we never want executed without explicit user override.
deny_patterns=(
  '(^|[;&|][[:space:]]*|[[:space:]])(/[^[:space:]]*/)?rm[[:space:]]+-[^[:space:]]*[rR][^[:space:]]*[fF][^[:space:]]*[[:space:]]+(/|~|\*)($|[[:space:]])'
  '(^|[;&|][[:space:]]*|[[:space:]])(/[^[:space:]]*/)?rm[[:space:]]+-[^[:space:]]*[fF][^[:space:]]*[rR][^[:space:]]*[[:space:]]+(/|~|\*)($|[[:space:]])'
  '(^|[;&|][[:space:]]*|[[:space:]])(/[^[:space:]]*/)?rm[[:space:]]+(-[rR]|--recursive)[[:space:]]+(-[fF]|--force)[[:space:]]+(/|~|\*)($|[[:space:]])'
  '(^|[;&|][[:space:]]*|[[:space:]])(/[^[:space:]]*/)?rm[[:space:]]+(-[fF]|--force)[[:space:]]+(-[rR]|--recursive)[[:space:]]+(/|~|\*)($|[[:space:]])'
  '(^|[;&|][[:space:]]*|[[:space:]])sudo[[:space:]]+(/[^[:space:]]*/)?rm([[:space:]]|$)'
  ':\(\)\{ :|:& \};:'        # fork bomb
  '(^|[;&|][[:space:]]*|[[:space:]])mkfs([.[:alnum:]_-]*)?([[:space:]]|$)'
  '(^|[;&|][[:space:]]*|[[:space:]])dd[[:space:]].*of=/dev/'
  '(^|[[:space:]])([Ff][Ll][Uu][Ss][Hh][Aa][Ll][Ll])($|[[:space:]])'
  '(^|[[:space:]])[Dd][Rr][Oo][Pp][[:space:]]+[Dd][Aa][Tt][Aa][Bb][Aa][Ss][Ee]($|[[:space:]])'
  '(^|[;&|][[:space:]]*|[[:space:]])git[[:space:]]+push([[:space:]]+[^[:space:]]+)*[[:space:]]+(--force([=-][^[:space:]]*)?|-f)([[:space:]]|$)'
  '(^|[;&|][[:space:]]*|[[:space:]])git[[:space:]]+reset[[:space:]]+--hard[[:space:]]+[[:alnum:]_.-]+/'
)

for pat in "${deny_patterns[@]}"; do
  if printf '%s\n' "$cmd" | grep -E -q "$pat"; then
    echo "Blocked by $0: matched pattern '$pat'." >&2
    echo "If this is intentional, run it yourself or remove the pattern from the hook." >&2
    exit 2
  fi
done

exit 0
