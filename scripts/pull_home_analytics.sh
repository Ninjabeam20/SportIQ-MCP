#!/usr/bin/env bash
# Copy Dell JSONL onto this Mac so scripts/dashboard.py can chart it.
# Read-only. Requires SSH alias `home-server` and a rebuilt sportiq container
# that mounts sportiq-analytics at /var/log/sportiq.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/analytics-archive/home-server"
mkdir -p "$DEST"
TMP="$DEST/events.jsonl.tmp"
if ssh home-server 'docker exec sportiq sh -c "cat /var/log/sportiq/events.jsonl 2>/dev/null; cat /var/log/sportiq/events.jsonl.1 2>/dev/null; true"' \
  > "$TMP"; then
  grep -v '^$' "$TMP" > "$DEST/events.jsonl" || true
  rm -f "$TMP"
  echo "Wrote $DEST/events.jsonl ($(wc -l < "$DEST/events.jsonl" | tr -d ' ') lines)"
else
  rm -f "$TMP"
  echo "Could not pull /var/log/sportiq/events.jsonl from home-server. Rebuild compose there first." >&2
  exit 1
fi
