# API budgets

Free-tier limits per source. NEVER bypass cache to "make sure data is fresh." Burning quota = whole tool dies for everyone.

| Source | Free-tier limit | Notes |
| :--- | :--- | :--- |
| CricAPI | 100 req/day | Token via `CRICAPI_KEY`. Hard daily cap — exhaust it and live scores die until reset. |
| NDTV Sports scraper | None (informal) | Opt-in (`SPORTIQ_ENABLE_NDTV=1`). Rate-limit to ≤1 req/3s to avoid IP block. |
| Cricbuzz scraper | None (informal) | Opt-in (`SPORTIQ_ENABLE_CRICBUZZ=1`). Rate-limit to ≤1 req/3s. ToS-risky; operator opt-in required. |
| RapidAPI Cricbuzz | Varies by plan | Token via `RAPIDAPI_KEY`. Free tier limited; paid plans from $10/mo. Paid escape hatch. |
| OpenF1 | None published | Free + public. Still cache aggressively; latency dominates. |
| Jolpica (Ergast successor) | None published | Free + public. Snapshot per session. |
| API-Football | 100 req/day (free tier) | Token via `APIFOOTBALL_KEY`. Premium = $19/mo for 7.5k/day. |
| football-data.org | 10 req/min, 100/day (free tier) | Token-less for free, but watch the per-minute cap. |
| The Odds API | 500 req/month (free tier) | Token via `THEODDS_KEY`. Shared across cricket + football (one `theodds` source). No per-month unit in `Budget`, so gated at a ~16/day slice; on exhaustion the chain serves stale odds (24h ceiling). Paid plans from $30/mo. |

## Enforcement

- `core/ratelimit.py` keeps per-source token buckets in Redis/diskcache.
- Before each adapter call, the chain checks budget. If exhausted, the chain skips that adapter and tries the next.
- `sportiq_health()` surfaces remaining quota per source.

## When you add a new source

Update this file. Update `.claude/rules/caching-policy.md` if it introduces a new data class.
