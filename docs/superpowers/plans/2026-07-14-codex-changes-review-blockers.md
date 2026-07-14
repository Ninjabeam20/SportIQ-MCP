# Codex Changes Review Blockers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan inline and task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Status:** Completed locally on `codex_changes` on 2026-07-14; full verification results are
recorded in `docs/log.md`.

**Goal:** Fix the four confirmed `codex_changes` merge blockers plus the adjacent mid-body disconnect defect without broadening the hosted-control or football-model scope.

**Architecture:** Preserve the existing pure-ASGI middleware, cache interface, and shared football ranking path. Each blocker gets a red-to-green regression test, the smallest localized implementation change, directly affected documentation, and its own local conventional commit; a trailing documentation commit records the resolved finding and exact commit references.

**Tech Stack:** Python 3.11+, pure ASGI, Starlette `Request`, `sse-starlette` `EventSourceResponse`, diskcache, redis-py 7.4.0, NumPy, pytest/pytest-asyncio, Ruff, Bandit.

## Global Constraints

- Work only on `codex_changes`; do not switch, merge, rebase, push, publish, or deploy.
- Do not call live sports APIs, Cloud Run, Redis, or any other external service.
- Preserve the existing `.gitignore` and `review-phase1-cleanup.md` user changes.
- The user-authored `docs/index.md` and `docs/wiki/findings/codex-changes-review-blockers.md` changes are in scope and may be updated, but not discarded.
- Keep GET/DELETE `/mcp` limiting, dead `simulate_group` removal, and group-simulation performance out of scope.
- Keep local diskcache healthy without a Redis daemon; Redis behavior is tested with fakes.
- Use red-to-green TDD and stage only the files named by the current task.
- Use four blocker commits plus one optional trailing documentation commit, all local, with `Co-Authored-By: OpenAI Codex <noreply@openai.com>`.

## Completed prerequisite

- Commit `8db98cf` makes both convenience format hooks fail open when an event has no usable
  `tool_input.file_path`, while the dangerous-command hooks remain fail closed. The hook suite
  covers malformed, missing-path, and patch-shaped events.

---

### Task 0: Reconfirm the protected worktree baseline

**Files:**
- Read only: repository state and the affected tests

**Interfaces:**
- Consumes: branch `codex_changes` and the user-owned dirty files
- Produces: a recorded baseline that prevents unrelated edits from being staged

- [x] **Step 1: Confirm branch and dirty files**

Run:

```bash
git branch --show-current
git status --short --branch
```

Expected: branch `codex_changes`; existing dirty state includes `.gitignore`, `docs/index.md`, `docs/wiki/findings/codex-changes-review-blockers.md`, and `review-phase1-cleanup.md`.

- [x] **Step 2: Run the affected baseline tests**

Run:

```bash
uv run pytest tests/unit/test_request_limits.py tests/unit/test_group_sim.py tests/unit/test_cache.py -q
```

Expected before new regressions: PASS. No live API is contacted.

### Task 1: Preserve hosted SSE responses and stop responding after upload disconnects

**Files:**
- Modify: `src/sportiq/core/request_limits.py:101-132`
- Modify: `tests/unit/test_request_limits.py`

**Interfaces:**
- Consumes: a buffered POST body, the original ASGI `receive`, and a downstream streaming response
- Produces: one replayed `http.request`, followed by delegation to the real `receive`; mid-body `http.disconnect` returns silently

- [x] **Step 1: Add the failing SSE regression**

Add a downstream app that consumes the body through the transport-style Starlette request API before starting SSE:

```python
class _StreamingApp:
    def __init__(self) -> None:
        self.body = b""

    async def __call__(self, scope, receive, send) -> None:
        request = Request(scope, receive)
        self.body = await request.body()

        async def events():
            for index in range(3):
                await asyncio.sleep(0)
                yield {"data": f"chunk-{index}"}

        await EventSourceResponse(events(), ping=None)(scope, receive, send)
```

Extend the test receive helper with a mode that blocks after the request body instead of fabricating a client disconnect:

```python
if messages:
    return messages.pop(0)
if disconnect_after_body:
    return {"type": "http.disconnect"}
await asyncio.Event().wait()
raise AssertionError("unreachable")
```

The regression must call the middleware with `disconnect_after_body=False`, assert `app.body == b"{}"`, combine all `http.response.body` chunks, and assert all three `data: chunk-N` events are present.

- [x] **Step 2: Add the failing mid-body disconnect regression**

Feed these messages directly to the middleware:

```python
[
    {"type": "http.request", "body": b"partial", "more_body": True},
    {"type": "http.disconnect"},
]
```

Assert the downstream app is never called and `send` receives no response messages.

- [x] **Step 3: Run both regressions and verify RED**

Run:

```bash
uv run pytest \
  tests/unit/test_request_limits.py::test_request_limit_preserves_sse_stream_after_body_replay \
  tests/unit/test_request_limits.py::test_request_limit_returns_silently_on_mid_body_disconnect -q
```

Expected: the SSE test sees no event chunks and the disconnect test sees an unwanted 400 response.

- [x] **Step 4: Implement the minimal receive fixes**

In the body loop, distinguish a real disconnect from other unexpected messages:

```python
message = await receive()
if message.get("type") == "http.disconnect":
    return
if message.get("type") != "http.request":
    await _json_response(send, 400, "incomplete request body")
    return
```

After the one buffered replay, delegate to the original receive:

```python
async def replay_receive() -> dict:
    nonlocal replayed
    if not replayed:
        replayed = True
        return {
            "type": "http.request",
            "body": bytes(body),
            "more_body": False,
        }
    return await receive()
```

- [x] **Step 5: Verify GREEN and commit blocker 1**

Run:

```bash
uv run pytest tests/unit/test_request_limits.py -q
uv run ruff check src/sportiq/core/request_limits.py tests/unit/test_request_limits.py
git diff --check -- src/sportiq/core/request_limits.py tests/unit/test_request_limits.py
```

Then stage only these two files and commit:

```text
fix(core): preserve SSE after request body replay

Co-Authored-By: OpenAI Codex <noreply@openai.com>
```

### Task 2: Correct the FIFA equal-points ranking tuple

**Files:**
- Modify: `src/sportiq/football/models/group_sim.py:64-73`
- Modify: `tests/unit/test_group_sim.py`
- Modify: `.agents/skills/monte-carlo-bracket/SKILL.md`
- Modify: `.claude/skills/monte-carlo-bracket/SKILL.md`
- Modify: `docs/wiki/models/group-sim.md`
- Modify: `docs/superpowers/specs/2026-07-14-codex-changes-hardening-correctness-design.md`
- Modify: `docs/superpowers/plans/2026-07-14-codex-changes-hardening-correctness.md`

**Interfaces:**
- Consumes: equal-overall-points cohorts plus already-computed head-to-head points/GF/GA and overall GF/GA
- Produces: `(h2h_points, h2h_gd, h2h_gf, overall_gd, overall_gf)` before the documented model-rating fallback

- [x] **Step 1: Add the failing two-team regression**

Lock all six group matches so `AAA` and `BBB` finish on four points, draw head-to-head 0-0, `AAA` has more overall goals, and `BBB` has the better overall goal difference:

```python
known = GroupResults(
    completed=[
        ("AAA", "BBB", 0, 0),
        ("AAA", "CCC", 5, 4),
        ("AAA", "DDD", 0, 3),
        ("BBB", "CCC", 2, 0),
        ("BBB", "DDD", 2, 3),
        ("CCC", "DDD", 0, 0),
    ],
    remaining=[],
)
```

Call `simulate_group_once` and assert `BBB` ranks above `AAA` after the head-to-head draw.

- [x] **Step 2: Add the failing three-team head-to-head-goals regression**

Use a three-team points cohort whose mini-league is:

```python
(
    ("AAA", "BBB", 2, 2),
    ("AAA", "CCC", 1, 1),
    ("BBB", "CCC", 0, 0),
)
```

Give `AAA`, `BBB`, and `CCC` one win each over `DDD`, with larger overall win margins for `BBB` and `CCC`. Assert the tied cohort ranks `AAA`, then `BBB`, then `CCC`, proving head-to-head goals precede overall fields.

- [x] **Step 3: Verify both tests fail for the existing tuple**

Run:

```bash
uv run pytest \
  tests/unit/test_group_sim.py::test_overall_goal_difference_beats_overall_goals_after_h2h_draw \
  tests/unit/test_group_sim.py::test_head_to_head_goals_rank_three_team_points_cohort -q
```

Expected: both fail because slot three currently uses `gf[team]`.

- [x] **Step 4: Replace only the incorrect tuple field**

Use:

```python
available_keys = {
    team: (
        h2h_points[team],
        h2h_gf[team] - h2h_ga[team],
        h2h_gf[team],
        gf[team] - ga[team],
        gf[team],
    )
    for team in cohort
}
```

Do not change `_rank_thirds`, the rating/RNG fallback, `simulate_group`, or iteration counts.

- [x] **Step 5: Correct every directly affected description**

In both skill copies, the group-sim wiki, and the existing branch design/plan, replace the incorrect third criterion with `head-to-head goals scored`. State that the current model applies the head-to-head criteria once to the equal-points cohort and does not iteratively reapply them to a shrinking sub-cohort. Do not claim conduct/FIFA-ranking inputs exist.

- [x] **Step 6: Verify GREEN and commit blocker 2**

Run:

```bash
uv run pytest tests/unit/test_group_sim.py tests/unit/test_bracket_sim.py -q
uv run ruff check src/sportiq/football/models/group_sim.py tests/unit/test_group_sim.py
git diff --check -- src/sportiq/football/models/group_sim.py tests/unit/test_group_sim.py .agents/skills/monte-carlo-bracket/SKILL.md .claude/skills/monte-carlo-bracket/SKILL.md docs/wiki/models/group-sim.md docs/superpowers
```

Commit only the files listed in this task:

```text
fix(football): use head-to-head goals in group tiebreaks

Co-Authored-By: OpenAI Codex <noreply@openai.com>
```

### Task 3: Trust only Cloud Run's rightmost forwarded IP

**Files:**
- Modify: `src/sportiq/core/request_limits.py:19-31`
- Modify: `tests/unit/test_request_limits.py`
- Modify: `SECURITY.md`
- Modify: `docs/wiki/decisions/0012-hosted-abuse-controls.md`
- Modify: `GAPS.md`
- Modify: `docs/superpowers/specs/2026-07-14-codex-changes-hardening-correctness-design.md`
- Modify: `docs/superpowers/plans/2026-07-14-codex-changes-hardening-correctness.md`

**Interfaces:**
- Consumes: Cloud Run's comma-separated `X-Forwarded-For` value
- Produces: the validated rightmost IP, or the ASGI peer address when the rightmost value is invalid/absent

- [x] **Step 1: Replace the old leftmost-hop unit expectation**

Use a scope containing:

```python
"headers": [(b"x-forwarded-for", b"203.0.113.7, 198.51.100.2")]
```

Assert trusted mode returns `198.51.100.2`. Then set the rightmost entry to `not-an-ip` and assert fallback to `scope["client"][0]`.

- [x] **Step 2: Add the rate-bucket bypass regression**

Construct middleware with `per_client_per_minute=1`, set `middleware.trust_forwarded = True`, and issue two requests with different spoofed first entries but the same rightmost IP:

```python
b"203.0.113.7, 198.51.100.2"
b"203.0.113.99, 198.51.100.2"
```

Assert the first response is 200, the second is 429, and the downstream app is called once.

- [x] **Step 3: Verify RED**

Run:

```bash
uv run pytest \
  tests/unit/test_request_limits.py::test_request_limit_uses_valid_rightmost_xff_on_cloud_run \
  tests/unit/test_request_limits.py::test_request_limit_spoofed_xff_prefix_cannot_rotate_buckets -q
```

Expected: the identity test returns the first IP and the bypass test admits both requests.

- [x] **Step 4: Select the rightmost entry**

Change only the candidate extraction and clarify the docstring:

```python
candidate = forwarded.rsplit(",", 1)[-1].strip()
```

Keep `ipaddress.ip_address` validation and the existing ASGI-peer fallback.

- [x] **Step 5: Correct directly affected hosted-control documentation**

Change `leftmost`/`head` wording to `rightmost`/`last entry appended by Cloud Run` in `SECURITY.md`, ADR-0012, `GAPS.md`, and the existing branch design/plan. Do not claim GET/DELETE requests are limited.

- [x] **Step 6: Verify GREEN and commit blocker 3**

Run:

```bash
uv run pytest tests/unit/test_request_limits.py -q
uv run ruff check src/sportiq/core/request_limits.py tests/unit/test_request_limits.py
git diff --check -- src/sportiq/core/request_limits.py tests/unit/test_request_limits.py docs/wiki/decisions/0012-hosted-abuse-controls.md GAPS.md docs/superpowers
```

Commit only the files listed in this task:

```text
fix(core): trust Cloud Run's rightmost forwarded IP

Co-Authored-By: OpenAI Codex <noreply@openai.com>
```

### Task 4: Recover legacy wrapped counters without masking Redis outages

**Files:**
- Modify: `src/sportiq/core/cache.py:139-164`
- Modify: `tests/unit/test_cache.py`

**Interfaces:**
- Consumes: legacy JSON-wrapped counter strings under current counter keys
- Produces: a reset raw counter value of `1`; only `redis.exceptions.ResponseError` and diskcache `TypeError` trigger reset/retry

- [x] **Step 1: Pin the installed Redis exception contract**

The local installed client is redis-py `7.4.0`. `ResponseError` and `ConnectionError` are sibling subclasses of `RedisError`, so catching `ResponseError` does not swallow connection failures. Import exactly:

```python
from redis.exceptions import ResponseError
```

- [x] **Step 2: Add the failing diskcache legacy-value regression**

Seed the raw disk backend directly:

```python
cache._disk.set(
    "counter:legacy-disk",
    '{"value":7,"stored_at":0}',
    expire=60,
)
```

Assert `await cache.incr_counter(...) == 1` and `await cache.get_counter(...) == 1` without changing backend.

- [x] **Step 3: Add Redis fake regressions for value and connection errors**

Create one fake whose first `eval` raises:

```python
ResponseError("value is not an integer or out of range")
```

Its `delete` marks the legacy key removed and its second `eval` returns `1`. Assert one delete, two evals, value `1`, and `cache.backend == "redis"`.

Create a second fake whose `eval` raises `redis.exceptions.ConnectionError`. Assert `delete` is never called, the cache downgrades to diskcache, and the disk counter returns `1`.

- [x] **Step 4: Verify RED**

Run:

```bash
uv run pytest \
  tests/unit/test_cache.py::test_counter_resets_legacy_wrapped_disk_value \
  tests/unit/test_cache.py::test_redis_counter_resets_only_response_errors \
  tests/unit/test_cache.py::test_redis_counter_connection_error_downgrades_without_delete -q
```

Expected: diskcache raises `TypeError`; Redis mode downgrades on the legacy `ResponseError` instead of deleting/retrying.

- [x] **Step 5: Add narrow reset-and-retry behavior**

Redis mode uses a nested `ResponseError` handler inside the existing connection-failure boundary:

```python
try:
    try:
        value = await self._redis.eval(script, 1, key, ttl_seconds)
    except ResponseError:
        await self._redis.delete(key)
        value = await self._redis.eval(script, 1, key, ttl_seconds)
    return int(value)
except Exception as e:
    self._downgrade_to_disk(e)
```

Disk mode retries only `TypeError` while retaining the existing transaction:

```python
with self._disk.transact():
    try:
        value = self._disk.incr(key, delta=1, default=0)
    except TypeError:
        self._disk.delete(key)
        value = self._disk.incr(key, delta=1, default=0)
    if value == 1:
        self._disk.expire(key, ttl_seconds)
```

Do not parse or preserve the legacy count; resetting the current window may admit one bounded extra request but avoids a tool crash or false Redis downgrade.

- [x] **Step 6: Verify GREEN and commit blocker 4**

Run:

```bash
uv run pytest tests/unit/test_cache.py tests/unit/test_ratelimit_atomic.py tests/unit/test_fallback_chain.py -q
uv run ruff check src/sportiq/core/cache.py tests/unit/test_cache.py
git diff --check -- src/sportiq/core/cache.py tests/unit/test_cache.py
```

Commit only these files:

```text
fix(core): recover legacy counter values on increment

Co-Authored-By: OpenAI Codex <noreply@openai.com>
```

### Task 5: Record resolution and run the final offline gate

**Files:**
- Modify: `docs/wiki/findings/codex-changes-review-blockers.md`
- Modify: `docs/index.md`
- Modify: `docs/log.md`
- Add: `docs/superpowers/plans/2026-07-14-codex-changes-review-blockers.md`

**Interfaces:**
- Consumes: the four blocker commit hashes and final verification output
- Produces: a truthful resolved finding, updated index line, project journal entry, and reviewable plan record

- [x] **Step 1: Update the finding with actual results**

Change the finding summary from “fixes planned” to “fixed”, record the four exact commit hashes/subjects, and retain the three explicitly deferred findings. Update `last_updated` only if the date changes.

- [x] **Step 2: Update the wiki index and journal**

Change the existing `docs/index.md` finding description to say the four blockers were fixed. Append one `## [2026-07-14] fix | resolve codex_changes review blockers` entry to `docs/log.md` summarizing SSE replay/disconnect, football tiebreaks, rightmost XFF, legacy counters, and the verification gate.

- [x] **Step 3: Run focused and full verification**

Run:

```bash
uv run pytest tests/unit/test_request_limits.py tests/unit/test_group_sim.py tests/unit/test_cache.py -q
uv run pytest
uv run ruff check .
uv run bandit -r src -ll --quiet
git diff --check
```

Expected: all commands exit 0; no live API, deploy, or publish action occurs. The SSE regression itself is the executable 3/3-chunk repro.

- [x] **Step 4: Commit the resolution documentation**

Stage only the three tracked documentation files listed in this task and commit. `docs/log.md`
remains intentionally gitignored while retaining its required local journal entry.

```text
docs: record review blocker fixes

Co-Authored-By: OpenAI Codex <noreply@openai.com>
```

- [x] **Step 5: Verify final history and protected files**

Run:

```bash
git log -5 --oneline
git status --short --branch
git diff HEAD -- .gitignore review-phase1-cleanup.md
```

Expected: four fix commits plus one documentation commit; `.gitignore` and `review-phase1-cleanup.md` remain exactly as the user left them; nothing was pushed, merged, or deployed.
