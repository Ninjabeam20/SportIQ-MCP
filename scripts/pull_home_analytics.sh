#!/usr/bin/env bash
# Copy Dell JSONL onto this Mac so scripts/dashboard.py can chart it.
# Read-only. Requires SSH alias `home-server` and a rebuilt sportiq container
# that mounts sportiq-analytics at /var/log/sportiq.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/analytics-archive/home-server"
mkdir -p "$DEST"
# Write to temp files in DEST and replace atomically, and only on a non-empty
# export: a reachable host with no readable logs must not erase the archive.
RAW="$(mktemp "$DEST/.events.raw.XXXXXX")"
OUT="$(mktemp "$DEST/.events.jsonl.XXXXXX")"
trap 'rm -f "$RAW" "$OUT"' EXIT
if ! ssh home-server 'docker exec sportiq sh -c "cat /var/log/sportiq/events.jsonl 2>/dev/null; cat /var/log/sportiq/events.jsonl.1 2>/dev/null; true"' \
  > "$RAW"; then
  echo "Could not pull /var/log/sportiq/events.jsonl from home-server. Rebuild compose there first." >&2
  exit 1
fi
grep -v '^$' "$RAW" > "$OUT" || true
if [ ! -s "$OUT" ]; then
  echo "Export from home-server was empty; kept the existing $DEST/events.jsonl." >&2
  exit 1
fi
mv "$OUT" "$DEST/events.jsonl"
echo "Wrote $DEST/events.jsonl ($(wc -l < "$DEST/events.jsonl" | tr -d ' ') lines)"
