---
title: diskcache expire() Purged the Whole Cache
type: finding
tags: [cache, diskcache, ratelimit, production-bug]
sources: [docs/audits/2026-10-22-full-audit.md, src/sportiq/core/cache.py]
last_updated: 2026-10-22
related: [[2026-10-22-full-audit]], [[0003-redis-with-diskcache-fallback]], [[stateless-lifespan-teardown]], [[codex-changes-review-blockers]]
---

# diskcache expire() Purged the Whole Cache

`Cache.incr_counter` called `self._disk.expire(key, ttl_seconds)` to give a counter a TTL, but diskcache's `expire(now=None, retry=False)` means "delete every expired item", so each first counter increment deleted every cached entry that had a TTL.

## Mechanism
- The key landed in the `now` parameter. diskcache compares `expire_time < now` in SQLite, and a REAL
  always sorts below TEXT, so every TTL'd row counted as expired and was deleted. The counter itself never
  received a TTL.
- `RequestLimitMiddleware` increments a per-minute counter on the first `POST /mcp` of each minute, so on
  the Dell cached data lived about one minute. Stale fallback almost never fired, and upstream quota was
  spent re-fetching data that should have been cached.
- Redis was unaffected (it has a real per-key `EXPIRE`); local dev and the Dell both run diskcache.

## Fix (2026-10-22)
Both `incr_counter` and `incr_counter_if_below` now call `self._disk.touch(key, expire=ttl_seconds)`.
Regression tests in `tests/unit/test_cache.py` set two long-TTL keys, increment a counter, and assert both
keys survive and the counter's own expiry is about `now + ttl`.

## Lesson
Same method name, different contract: in diskcache `expire` is a purge and `touch` sets a TTL. Changing
the cache's counter path needs a test that checks **other** keys survive, not only the counter's value.
