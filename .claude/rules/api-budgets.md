# API budgets

Free-tier limits per source. NEVER bypass cache to "make sure data is fresh." Burning quota = whole tool dies for everyone.

| Source | Free-tier limit | Notes |
| :--- | :--- | :--- |
| CricAPI | 100 req/day | Token via `CRICAPI_KEY`. Hard daily cap — exhaust it and live scores die until reset. |
| Cricbuzz scraper | None (informal) | Rate-limit ourselves to ≤1 req/3s to avoid IP block. |
| OpenF1 | None published | Free + public. Still cache aggressively; latency dominates. |
| Jolpica (Ergast successor) | None published | Free + public. Snapshot per session. |
| API-Football | 100 req/day (free tier) | Token via `APIFOOTBALL_KEY`. Premium = $19/mo for 7.5k/day. |
| football-data.org | 10 req/min, 100/day (free tier) | Token-less for free, but watch the per-minute cap. |

## Enforcement

- `core/ratelimit.py` keeps per-source token buckets in Redis/diskcache.
- Before each adapter call, the chain checks budget. If exhausted, the chain skips that adapter and tries the next.
- `sportiq_health()` surfaces remaining quota per source.

## When you add a new source

Update this file. Update `.claude/rules/caching-policy.md` if it introduces a new data class.
