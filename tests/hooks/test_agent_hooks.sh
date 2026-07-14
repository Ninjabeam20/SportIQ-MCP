#!/usr/bin/env bash

set -euo pipefail

assert_exit() {
  expected="$1"
  input="$2"
  hook="$3"
  set +e
  printf '%s' "$input" | "$hook" >/dev/null 2>&1
  actual="$?"
  set -e
  if [[ "$actual" -ne "$expected" ]]; then
    echo "$hook: expected $expected, got $actual for $input" >&2
    exit 1
  fi
}

tmp_dir="$(mktemp -d tests/hooks/tmp.XXXXXX)"
trap 'rm -rf "$tmp_dir"' EXIT

for root in .claude .codex; do
  block_hook="$root/hooks/block-dangerous-bash.sh"
  format_hook="$root/hooks/format-on-save.sh"

  assert_exit 2 '{"tool_input":{"command":"rm -rf /"}}' "$block_hook"
  assert_exit 2 '{"tool_input":{"command":"/bin/rm -fr /"}}' "$block_hook"
  assert_exit 2 '{"tool_input":{"command":"git push --force origin main"}}' "$block_hook"
  assert_exit 2 '{"tool_input":{"command":"git reset --hard origin/main"}}' "$block_hook"
  assert_exit 0 '{"tool_input":{"command":"uv run pytest"}}' "$block_hook"
  assert_exit 2 '{broken-json' "$block_hook"
  assert_exit 2 '{"tool_input":{}}' "$block_hook"

  python_file="$tmp_dir/${root#.}.py"
  text_file="$tmp_dir/${root#.}.txt"
  printf 'x=  1\n' >"$python_file"
  printf 'x=  1\n' >"$text_file"

  assert_exit 0 "{\"tool_input\":{\"file_path\":\"$python_file\"}}" "$format_hook"
  assert_exit 0 "{\"tool_input\":{\"file_path\":\"$text_file\"}}" "$format_hook"
  assert_exit 0 '{broken-json' "$format_hook"
  assert_exit 0 '{"tool_input":{}}' "$format_hook"
  assert_exit 0 '{"tool_input":{"patch":"*** Begin Patch"}}' "$format_hook"

  test "$(cat "$python_file")" = 'x = 1'
  test "$(cat "$text_file")" = 'x=  1'
done
