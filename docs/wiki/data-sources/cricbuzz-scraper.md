---
title: Cricbuzz Scraper
type: data-source
tags: [cricket, live-scores, scraper, opt-in]
sources: []
last_updated: 2026-05-26
related: [[cricket-live-score-chain]], [[0007-cricket-fallback-strategy]]
---

# Cricbuzz Scraper

BeautifulSoup + httpx scraper against `m.cricbuzz.com` (mobile site). Opt-in fallback for live scores. Cricbuzz's ToS prohibits scraping; this adapter is **disabled by default** in the shipped package.

## Enabling

```
SPORTIQ_ENABLE_CRICBUZZ=1
```

## Adapter behavior

- Constructor never raises.
- `healthcheck()` returns `True` only if `SPORTIQ_ENABLE_CRICBUZZ=1`.
- `fetch()` raises `MissingCredentialsError` when disabled — chain skips silently.
- Parsed output is `{"matches": [{"raw": "<text>"}]}` from `.cb-mtch-lst` elements.

## Rate limiting

Informal. Uses mobile user-agent. Self-rate-limited to ≤1 req/3s.

## Test fixtures

`tests/fixtures/cricbuzz/live_page.html` — minimal mobile HTML with two match listings.

See [[0007-cricket-fallback-strategy]] for the ToS rationale and RapidAPI as the paid escape hatch.
