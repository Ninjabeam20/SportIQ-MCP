---
title: NDTV Sports Scraper
type: data-source
tags: [cricket, live-scores, fixtures, scraper, opt-in]
sources: []
last_updated: 2026-05-26
related: [[cricket-live-score-chain]], [[cricket-fixtures-chain]], [[0007-cricket-fallback-strategy]]
---

# NDTV Sports Scraper

BeautifulSoup + httpx scraper against `sports.ndtv.com`. Opt-in fallback for live scores and fixtures. NDTV's ToS has informal restrictions on automated scraping; this adapter is **disabled by default** in the shipped package.

## Enabling

```
SPORTIQ_ENABLE_NDTV=1
```

## Adapter behavior

- Constructor never raises.
- `healthcheck()` returns `True` only if `SPORTIQ_ENABLE_NDTV=1`.
- `fetch()` raises `MissingCredentialsError` when disabled — the chain walks past it silently.
- Parsed output is `{"matches": [{"raw": "<text>"}]}`. Raw text is extracted from `.match-card` elements.

## Rate limiting

No formal limit. Self-rate-limited to ≤1 req/3s by `core/ratelimit.py` to avoid IP block.

## Test fixtures

`tests/fixtures/ndtv_sports/live_page.html` — captured HTML with two `.match-card` divs.

See [[0007-cricket-fallback-strategy]] for the ToS rationale.
