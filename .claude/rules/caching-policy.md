# Caching policy

`core/cache.py` exposes one interface (`get`, `set`, `get_with_age`). Backend is Redis if `REDIS_URL` is set and reachable, else `diskcache` at `~/.cache/sportiq/`. Tools do not care which.

## TTL table

| Data class | Fresh TTL | Stale-ok ceiling |
| :--- | :--- | :--- |
| Live cricket scorecard | 30s | 5min (flagged) |
| F1 live telemetry (only if OpenF1 live auth is ever wired; none today) | 10s | 1min (flagged) |
| F1 completed-session laps/stints | 24h | 7d |
| Fixtures / schedule (static) | 6h | 24h |
| Live-tournament fixtures + results (football WC) — while a tournament is in progress; WC 2026 fixtures use the static class since the 2026-07-19 final | 30min | 24h |
| Standings / points table (exception: `f1_standings` 24h / 7d — updates once per race weekend) | 10min | 1h |
| Player career stats | 24h | 7d |
| Squad rosters | 12h | 3d |
| Bookmaker odds (h2h) | 5min | 24h (flagged) |
| Static seeds | ∞ | ∞ |
| Fallback attempt log | 7d | n/a |

## Key pattern

Keys are `sportiq:{sport}:{category}:{readable_args}` where `readable_args` is a
colon-joined string of the inputs (e.g. `sportiq:cricket:fixtures:ipl2026`,
`sportiq:cricket:squad:MI:none`). Use `none` / `all` for absent optional args.

Hashing is only required when args are unbounded or contain user-supplied
strings that could include `:` or `*` — in that case hash with
`hashlib.blake2s(..., digest_size=8).hexdigest()`.

Rate-limit counters use `ratelimit:{source}:{minute|day}`.

## Hard rules

- NEVER bypass cache to "make sure data is fresh." Adjust the TTL instead.
- NEVER write code that assumes Redis is running locally. The dev default is `diskcache`.
- Cache writes happen inside `FallbackChain.fetch()`, not in adapters.
