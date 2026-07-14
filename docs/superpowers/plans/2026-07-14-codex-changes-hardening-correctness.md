# Codex Changes Hardening and Football Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the verified security/runtime defects and correct World Cup qualification/result behavior in five ordered, independently verified batches on `codex_changes`.

**Architecture:** Preserve the existing FastMCP → tool → FallbackChain → adapter/model layering. Add pure-ASGI HTTP admission control and cache-backed atomic counters at the core boundary, then make targeted tool/model corrections without a framework rewrite. Public compatibility is retained through the envelope and existing `p_advance` key.

**Tech Stack:** Python 3.11+, FastMCP, pure ASGI, diskcache/optional Redis, httpx, NumPy, pytest/pytest-asyncio/respx, Ruff, Bandit, shell tests.

## Global Constraints

- Execute only on branch `codex_changes`; never switch, merge, rebase, push, or commit to `main`.
- Never deploy or mutate Cloud Run, Vercel, provider accounts, registries, or production.
- Never call live sports APIs or regenerate committed datasets from the network.
- Never stage or modify the pre-existing `.gitignore` edit or `review-phase1-cleanup.md`.
- Every tool continues to route through `FallbackChain` and return `Envelope` success/error shapes.
- Local development and tests use diskcache as a healthy state and require no Redis daemon.
- Preserve football → F1 → cricket ordering and the `sportiq.server:main` uvx contract.
- Use test-first red→green cycles and stage only files named by the current task.

---

### Task 0: Establish the branch baseline

**Files:**
- Read only: repository state

**Interfaces:**
- Consumes: branch `codex_changes` at design commit `9500e1a`
- Produces: verified pre-change baseline and a list of pre-existing dirty files to preserve

- [ ] **Step 1: Verify branch and protected dirty files**

Run:

```bash
git branch --show-current
git status --short --branch
```

Expected: branch is `codex_changes`; only `.gitignore` and `review-phase1-cleanup.md` are pre-existing user changes.

- [ ] **Step 2: Run the full offline baseline**

Run:

```bash
uv run pytest
uv run ruff check .
```

Expected: both exit 0. If either fails, stop and report the baseline failure before implementation.

### Task 1: Repair and regression-test both hook surfaces

**Files:**
- Create: `tests/hooks/test_agent_hooks.sh`
- Modify: `.claude/hooks/block-dangerous-bash.sh`
- Modify: `.claude/hooks/format-on-save.sh`
- Modify: `.codex/hooks/block-dangerous-bash.sh`
- Modify: `.codex/hooks/format-on-save.sh`
- Modify: `.codex/hooks.json`

**Interfaces:**
- Consumes: Claude/Codex hook JSON on stdin with `tool_input.command` or `tool_input.file_path`
- Produces: exit 0 for allowed input, exit 2 for rejected/malformed input, and relative Codex hook commands

- [ ] **Step 1: Write the failing shell regression test**

Create an executable script whose core assertions are:

```bash
assert_exit() {
  expected="$1"
  input="$2"
  hook="$3"
  set +e
  printf '%s' "$input" | "$hook" >/dev/null 2>&1
  actual="$?"
  set -e
  test "$actual" -eq "$expected" || {
    echo "$hook: expected $expected, got $actual for $input" >&2
    exit 1
  }
}

for root in .claude .codex; do
  hook="$root/hooks/block-dangerous-bash.sh"
  assert_exit 2 '{"tool_input":{"command":"rm -rf /"}}' "$hook"
  assert_exit 2 '{"tool_input":{"command":"/bin/rm -fr /"}}' "$hook"
  assert_exit 2 '{"tool_input":{"command":"git push --force origin main"}}' "$hook"
  assert_exit 2 '{"tool_input":{"command":"git reset --hard origin/main"}}' "$hook"
  assert_exit 0 '{"tool_input":{"command":"uv run pytest"}}' "$hook"
  assert_exit 2 '{broken-json' "$hook"
  assert_exit 2 '{"tool_input":{}}' "$hook"
done
```

The same script must create a temporary Python file containing `x=  1`, feed its path to both format hooks, assert the file becomes `x = 1`, and assert a temporary `.txt` file is unchanged.

- [ ] **Step 2: Verify the test fails for the reproduced root cause**

Run:

```bash
bash tests/hooks/test_agent_hooks.sh
```

Expected: FAIL because destructive and malformed input currently exit 0.

- [ ] **Step 3: Implement single-channel JSON parsing and fail-closed behavior**

In both destructive hooks, replace the heredoc/here-string parser with this extraction shape:

```bash
set -u
input="$(cat)"
if ! cmd="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    command = data["tool_input"]["command"]
    if not isinstance(command, str) or not command.strip():
        raise ValueError("missing command")
except Exception as exc:
    print(f"invalid hook input: {exc}", file=sys.stderr)
    raise SystemExit(2)
print(" ".join(command.split()))
')"; then
  exit 2
fi
```

Use narrowly scoped regexes that catch `rm` with combined/reordered recursive+force flags, absolute `rm`, force push, and hard reset to a remote ref while preserving safe commands.

In both format hooks, extract a nonempty string `tool_input.file_path` with the same `python3 -c` pattern; malformed input exits 2. Keep Python-only formatting and best-effort Ruff execution unchanged.

Set `.codex/hooks.json` commands exactly to:

```json
"command": "./.codex/hooks/block-dangerous-bash.sh"
```

and:

```json
"command": "./.codex/hooks/format-on-save.sh"
```

- [ ] **Step 4: Verify the hook suite passes**

Run:

```bash
chmod +x tests/hooks/test_agent_hooks.sh
bash tests/hooks/test_agent_hooks.sh
git diff --check -- .claude/hooks .codex/hooks .codex/hooks.json tests/hooks
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit Batch 1 only**

```bash
git add .claude/hooks .codex/hooks .codex/hooks.json tests/hooks/test_agent_hooks.sh
git commit -m "fix: repair agent command hooks"
```

### Task 2: Correct README and SECURITY claims

**Files:**
- Modify: `README.md`
- Modify: `SECURITY.md`
- Create: `tests/unit/test_public_claims.py`

**Interfaces:**
- Consumes: actual telemetry/key/payload behavior before hosted controls
- Produces: public documentation that makes no claim stronger than the current branch implementation

- [ ] **Step 1: Add a failing documentation-contract test**

Create assertions in `tests/unit/test_public_claims.py` that read both documents and require:

```python
from pathlib import Path


def test_public_docs_do_not_claim_zero_telemetry_or_host_secrets():
    readme = Path("README.md").read_text()
    security = Path("SECURITY.md").read_text()
    forbidden = ("No data collection.", "zero API keys", "all 44 tools work out of the box")
    assert all(claim not in readme for claim in forbidden)
    assert "zero API keys" not in security


def test_security_docs_do_not_advertise_unenforced_output_limits():
    security = Path("SECURITY.md").read_text()
    assert "Tools cap list payloads at 200 items" not in security
    assert "no application-level MCP request-size limit" in security


def test_security_reporting_discourages_public_disclosure():
    security = Path("SECURITY.md").read_text()
    assert "Do not open a public issue" in security
```

- [ ] **Step 2: Verify the documentation test fails**

Run:

```bash
uv run pytest tests/unit/test_public_claims.py -q
```

Expected: FAIL on the existing claims.

- [ ] **Step 3: Rewrite only the contradicted sections**

README must include a compact capability table with rows for hosted, local keyless, and local BYO-key use; state that all tools register but live/provider-backed availability depends on host/operator keys and quota.

README/SECURITY must state:

- telemetry fields: client software name/version, User-Agent, tool name, outcome, latency, source, and staleness;
- Cloud Run platform logs may contain network/request metadata;
- local stdio emits local logs but sends no SportIQ-host telemetry;
- the public host may carry operator credentials and the repository does not claim its unverified current key inventory;
- there is currently no application-level MCP request-size limit;
- upstream responses are rejected above 10 MiB only after httpx buffering;
- output limits are tool-specific, not universal;
- sensitive vulnerabilities go to the existing email and must not be opened publicly.

Keep historical review dates and describe them only as historical automated reviews, not current certification.

- [ ] **Step 4: Verify and commit Batch 2**

Run:

```bash
uv run pytest tests/unit/test_public_claims.py -q
uv run ruff check tests/unit/test_public_claims.py
git diff --check -- README.md SECURITY.md tests/unit/test_public_claims.py
```

Then:

```bash
git add README.md SECURITY.md tests/unit/test_public_claims.py
git commit -m "docs: correct security and telemetry claims"
```

### Task 3: Add atomic cache counters and migrate provider consumption

**Files:**
- Modify: `src/sportiq/core/cache.py`
- Modify: `src/sportiq/core/ratelimit.py`
- Modify: `tests/unit/test_cache.py`
- Create: `tests/unit/test_ratelimit_atomic.py`

**Interfaces:**
- Produces: `Cache.get_counter(key: str) -> int` and `Cache.incr_counter(key: str, ttl_seconds: int) -> int`
- Consumes: counter values as raw integers separate from normal `_encode`/`_decode` cache records

- [ ] **Step 1: Write failing diskcache counter tests**

Add tests that assert:

```python
async def test_counter_increment_is_atomic_under_concurrency():
    cache = get_cache()
    values = await asyncio.gather(
        *(cache.incr_counter("counter:atomic", ttl_seconds=60) for _ in range(50))
    )
    assert sorted(values) == list(range(1, 51))
    assert await cache.get_counter("counter:atomic") == 50


async def test_counter_is_separate_from_wrapped_cache_values():
    cache = get_cache()
    await cache.incr_counter("counter:raw", ttl_seconds=60)
    assert await cache.get_counter("counter:raw") == 1
    assert await cache.get("counter:raw") is None
```

Add a rate-limit test that constructs `Budget(source="atomic-test", per_day=100)`, runs 50 concurrent `consume(budget)` calls, and asserts `remaining(budget)["per_day"] == 50`.

- [ ] **Step 2: Verify RED**

```bash
uv run pytest tests/unit/test_cache.py tests/unit/test_ratelimit_atomic.py -q
```

Expected: FAIL because the counter methods do not exist and `consume()` loses concurrent increments.

- [ ] **Step 3: Implement dedicated raw counter operations**

Diskcache implementation must run increment plus first-write expiry in one transaction:

```python
with self._disk.transact():
    value = self._disk.incr(key, delta=1, default=0)
    if value == 1:
        self._disk.expire(key, ttl_seconds)
return int(value)
```

Redis implementation must use one Lua evaluation:

```python
value = await self._redis.eval(
    "local v=redis.call('INCR',KEYS[1]); "
    "if v==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return v",
    1,
    key,
    ttl_seconds,
)
```

`get_counter()` returns 0 for missing/non-integer values and follows the existing Redis→diskcache downgrade behavior. Normal `get()` treats a raw counter entry as a miss rather than trying to decode it.

Rewrite `consume()` to call `incr_counter()` for each configured window; rewrite `has_budget()` and `remaining()` to call `get_counter()`.

- [ ] **Step 4: Verify and commit the atomic-counter slice**

```bash
uv run pytest tests/unit/test_cache.py tests/unit/test_ratelimit_atomic.py tests/unit/test_fallback_chain.py -q
uv run ruff check src/sportiq/core/cache.py src/sportiq/core/ratelimit.py tests/unit/test_cache.py tests/unit/test_ratelimit_atomic.py
```

Then:

```bash
git add src/sportiq/core/cache.py src/sportiq/core/ratelimit.py tests/unit/test_cache.py tests/unit/test_ratelimit_atomic.py
git commit -m "fix(core): make quota counters atomic"
```

### Task 4: Add pure-ASGI request admission controls

**Files:**
- Create: `src/sportiq/core/request_limits.py`
- Create: `tests/unit/test_request_limits.py`
- Modify: `src/sportiq/config.py`
- Modify: `src/sportiq/server.py`
- Modify: `tests/unit/test_client_info_middleware.py`
- Modify: `src/sportiq/core/client_info.py`

**Interfaces:**
- Produces: `RequestLimitMiddleware(app, *, max_body_bytes, per_client_per_minute, global_per_minute)`
- Consumes: `Cache.incr_counter`, ASGI scope/receive/send, and Cloud Run's `K_SERVICE` trust boundary

- [ ] **Step 1: Write failing middleware tests**

Cover these behaviors with an inert downstream ASGI app and exact tests named
`test_request_limit_rejects_declared_oversize_before_downstream`,
`test_request_limit_rejects_chunked_oversize_at_one_byte_over_limit`,
`test_request_limit_replays_accepted_body_byte_for_byte`,
`test_request_limit_returns_429_with_retry_after_per_client`,
`test_request_limit_returns_429_at_global_ceiling_across_clients`,
`test_request_limit_ignores_xff_outside_cloud_run`,
`test_request_limit_uses_valid_leftmost_xff_on_cloud_run`, and
`test_request_limit_passes_get_and_non_mcp_requests_unchanged`. Each rejection
asserts the exact HTTP status, the `Retry-After` header where applicable, and that
the downstream call counter remains zero; the replay test asserts byte-for-byte
equality with the original multi-chunk body.

Use small injected limits (for example body 8 bytes, client 2/minute, global 3/minute) and assert rejected requests never increment the downstream call counter.

Add config tests asserting `http_max_body_bytes == 1_048_576`,
`http_rate_limit_per_minute == 60`, `http_global_rate_limit_per_minute == 300`,
and `expensive_tool_concurrency == 2`, and that zero/negative overrides fail
validation.

- [ ] **Step 2: Verify RED**

```bash
uv run pytest tests/unit/test_request_limits.py tests/unit/test_client_info_middleware.py -q
```

Expected: FAIL because the middleware/settings/capture limits do not exist.

- [ ] **Step 3: Implement request limiting**

`request_limits.py` exposes `_client_identity(scope: dict, *, trust_forwarded: bool) -> str`,
which trusts a validated leftmost XFF IP only when `trust_forwarded` is true and
otherwise uses `scope["client"][0]`, falling back to `"unknown"`. It also exposes
`_json_response(send, status: int, message: str, retry_after: int | None = None) -> None`,
which sends compact UTF-8 `application/json` with `Content-Length` and optional
`Retry-After`.

For accepted POST `/mcp` requests, increment the hashed per-client window first, reject if above 60, then increment/reject the global window. Validate `Content-Length` before reading. Read at most `max_body_bytes + 1`, return 413 on overflow, and replay one accepted `http.request` message containing the exact concatenated bytes.

Wire middleware order in `server.py` as:

```python
app.add_middleware(ClientInfoMiddleware)
app.add_middleware(RequestLimitMiddleware)
app.add_middleware(LegacyKeyPathMiddleware)
```

where last-added remains outermost. Delete the unused `_SERVER_SEMAPHORE`.

- [ ] **Step 4: Bound and sanitize client telemetry**

In `client_info.py`, keep at most 64 KiB of body for initialize inspection while forwarding every byte. Add a helper that strips control characters, trims whitespace, and caps client name/version at 100 characters and User-Agent at 300 characters. Tests must prove a larger body is forwarded intact while the captured inspection buffer is bounded.

- [ ] **Step 5: Verify middleware behavior and server wiring**

```bash
uv run pytest tests/unit/test_request_limits.py tests/unit/test_client_info_middleware.py tests/unit/test_path_compat_middleware.py -q
uv run ruff check src/sportiq/core/request_limits.py src/sportiq/core/client_info.py src/sportiq/config.py src/sportiq/server.py tests/unit/test_request_limits.py tests/unit/test_client_info_middleware.py
```

- [ ] **Step 6: Commit request admission controls**

```bash
git add src/sportiq/core/request_limits.py src/sportiq/core/client_info.py src/sportiq/config.py src/sportiq/server.py tests/unit/test_request_limits.py tests/unit/test_client_info_middleware.py
git commit -m "feat(core): bound hosted MCP requests"
```

### Task 5: Bound expensive-tool concurrency and document hosted policy

**Files:**
- Modify: `src/sportiq/core/tool_telemetry.py`
- Modify: `tests/unit/test_tool_telemetry.py`
- Modify: `README.md`
- Modify: `SECURITY.md`
- Modify: `cloud.md`
- Create: `docs/wiki/decisions/0012-hosted-abuse-controls.md`
- Modify: `docs/index.md`

**Interfaces:**
- Consumes: `settings.expensive_tool_concurrency`
- Produces: one shared semaphore around the five named expensive tool paths and durable abuse-control documentation

- [ ] **Step 1: Write the failing concurrency test**

Use an async probe function that increments an active counter, waits on an event, and records peak concurrency. Wrap it through the telemetry helper as `football_simulate_bracket`, launch four tasks, and assert the configured limit of two is never exceeded. Add a cheap-tool test proving four cheap calls can all enter.

- [ ] **Step 2: Verify RED**

```bash
uv run pytest tests/unit/test_tool_telemetry.py -q
```

Expected: FAIL because telemetry currently has no semaphore.

- [ ] **Step 3: Implement the named-tool semaphore**

Define exactly:

```python
_EXPENSIVE_TOOLS = frozenset({
    "football_simulate_group",
    "football_simulate_bracket",
    "football_knockout_path",
    "f1_predict_pit_strategy",
    "cricket_build_dream11_team",
})
```

Create one semaphore inside `instrument_tools()` and pass it into `_instrument()`. Await it only for names in `_EXPENSIVE_TOOLS`; keep telemetry timing outside the wait so latency includes queue time.

- [ ] **Step 4: Write ADR-0012 and update public controls**

The ADR frontmatter must use `type: decision`, link request limiting/cache/telemetry, and record:

- 1 MiB request body, 60 client requests/minute, 300 global requests/minute;
- Cloud Run-only trust of validated leftmost XFF;
- 64 KiB telemetry capture and concurrency 2;
- per-process counters plus the required one-instance deployment invariant;
- stdio unaffected; 413/429 occur before MCP envelopes;
- Cloud Run was not changed by this branch.

Update README/SECURITY from Task 2's “no app limit yet” wording to the exact implemented controls. Update `cloud.md` to show `--max-instances=1` as a required future deploy flag but do not run it.

- [ ] **Step 5: Verify and commit the hosted-control batch**

```bash
uv run pytest tests/unit/test_tool_telemetry.py tests/unit/test_request_limits.py tests/unit/test_public_claims.py -q
uv run ruff check src/sportiq/core/tool_telemetry.py tests/unit/test_tool_telemetry.py
git diff --check -- README.md SECURITY.md cloud.md docs/wiki/decisions/0012-hosted-abuse-controls.md docs/index.md
```

Then:

```bash
git add src/sportiq/core/tool_telemetry.py tests/unit/test_tool_telemetry.py README.md SECURITY.md cloud.md docs/wiki/decisions/0012-hosted-abuse-controls.md docs/index.md
git commit -m "feat: add hosted abuse guardrails"
```

### Task 6: Fix expected-error envelopes and relative redirects

**Files:**
- Modify: `src/sportiq/core/http.py`
- Modify: `src/sportiq/football/tools.py`
- Modify: `src/sportiq/football/intel_tools.py`
- Modify: `src/sportiq/f1/tools.py`
- Modify: `src/sportiq/f1/intel_tools.py`
- Modify: `tests/unit/test_s6_http_hardening.py`
- Modify: `tests/tools/test_football_tools.py`
- Modify: `tests/tools/test_f1_tools.py`

**Interfaces:**
- Consumes: chain-raised `NotFoundError`, HTTP `Location`
- Produces: `NOT_FOUND` envelopes and safe resolution of legal relative redirects

- [ ] **Step 1: Write failing regressions**

Add a respx 302 from `/v1/data` to `/v2/data` and assert `get_json()` returns the final JSON. Add scheme-change and port-change redirects and assert they are blocked.

For each sport, stub a representative raw chain and intel chain to raise `NotFoundError("missing")`; assert the tool returns:

```python
assert result["error"]["code"] == "NOT_FOUND"
```

and does not raise.

- [ ] **Step 2: Verify RED**

```bash
uv run pytest tests/unit/test_s6_http_hardening.py tests/tools/test_football_tools.py tests/tools/test_f1_tools.py -q
```

Expected: relative redirect and uncaught NotFound regressions fail.

- [ ] **Step 3: Implement URL resolution and exact error handling**

Resolve first, then compare normalized `(scheme, hostname, port)`:

```python
resolved = urljoin(str(response.request.url), location)
original = urlparse(str(response.request.url))
target = urlparse(resolved)
if (target.scheme, target.hostname, target.port) != (
    original.scheme, original.hostname, original.port
):
    raise httpx.HTTPStatusError(
        f"Cross-origin redirect blocked: {original.netloc!r} -> {target.netloc!r}",
        request=response.request,
        response=response,
    )
response = await client.get(resolved, **kwargs)
```

Import `NotFoundError` and widen only chain-boundary handlers. Build `NOT_FOUND` with the existing cricket pattern; retain `ALL_SOURCES_FAILED` for other chain failures.

- [ ] **Step 4: Verify and commit**

```bash
uv run pytest tests/unit/test_s6_http_hardening.py tests/tools/test_football_tools.py tests/tools/test_f1_tools.py -q
uv run ruff check src/sportiq/core/http.py src/sportiq/football/tools.py src/sportiq/football/intel_tools.py src/sportiq/f1/tools.py src/sportiq/f1/intel_tools.py
```

Then stage the named files and commit:

```bash
git commit -m "fix(core): preserve envelopes for expected misses"
```

### Task 7: Add cache lifecycle/corruption recovery and health identities

**Files:**
- Modify: `src/sportiq/core/cache.py`
- Modify: `src/sportiq/core/health.py`
- Modify: `src/sportiq/server.py`
- Modify: `tests/conftest.py`
- Modify: `tests/unit/test_cache.py`
- Modify: `tests/unit/test_health.py`
- Create: `tests/unit/test_server_lifecycle.py`
- Modify: `src/sportiq/football/adapters/static_seed.py`
- Modify: `src/sportiq/cricket/adapters/static_seed.py`
- Modify: `src/sportiq/football/adapters/theodds.py`
- Modify: `src/sportiq/cricket/adapters/theodds.py`

**Interfaces:**
- Produces: `Cache.delete(key)`, `Cache.close()`, `close_cache()`, and optional adapter `health_name`
- Consumes: malformed wrapped cache payloads and registered adapter instances

- [ ] **Step 1: Write failing cache and health tests**

Add tests that inject `"not-json"` into diskcache, call `cache.get(key)`, assert `None`, and assert the corrupt key was evicted. Add a close test that confirms the disk backend closes without ResourceWarning.

Add health registration tests with two adapters named `static_seed` but health names `football_static_seed` and `cricket_static_seed`, plus two `theodds` adapters sharing `health_name="theodds"`; assert statuses retain both statics and one odds entry.

- [ ] **Step 2: Verify RED**

```bash
uv run pytest tests/unit/test_cache.py tests/unit/test_health.py -q
```

- [ ] **Step 3: Implement lifecycle and corruption recovery**

`get()` catches decode/type/key errors, logs `cache.entry.corrupt` with only the key/backend/error type, deletes that key, and returns `None`. `delete()` delegates to Redis/diskcache with downgrade semantics. `close()` awaits Redis `aclose()` or closes diskcache, then clears handles. `close_cache()` closes and resets the singleton.

Define a FastMCP lifespan in `server.py`:

```python
@asynccontextmanager
async def _lifespan(_server):
    try:
        yield {}
    finally:
        await close_client()
        await close_cache()
```

Construct `FastMCP("sportiq", lifespan=_lifespan)`. The lifecycle test enters this
context, initializes both singletons, exits, and asserts both module-level singleton
references are reset.

Make `isolated_cache` an async fixture or register a finalizer that closes the per-test singleton before resetting it. Rewrite its stale docstring to explain credential isolation applies to any adapter `fetch()`, not healthchecks.

`register_adapter_for_health()` deduplicates on:

```python
getattr(adapter, "health_name", adapter.name)
```

and `get_health_report()` emits the same identity. Set only related adapter class attributes; do not change response `name`/`source`.

- [ ] **Step 4: Verify under ResourceWarning errors and commit**

```bash
uv run pytest -W error::ResourceWarning tests/unit/test_cache.py tests/unit/test_health.py tests/unit/test_server_lifecycle.py tests/tools/test_health_tool.py -q
uv run ruff check src/sportiq/core/cache.py src/sportiq/core/health.py src/sportiq/server.py tests/conftest.py tests/unit/test_cache.py tests/unit/test_health.py tests/unit/test_server_lifecycle.py
```

Stage only named files and commit:

```bash
git commit -m "fix(core): close caches and preserve health identities"
```

### Task 8: Close verified public input-bound gaps

**Files:**
- Modify: `src/sportiq/football/intel_tools.py`
- Modify: `src/sportiq/f1/tools.py`
- Modify: `src/sportiq/f1/intel_tools.py`
- Modify: `src/sportiq/cricket/intel_tools.py`
- Modify: `tests/tools/test_football_tools.py`
- Modify: `tests/tools/test_f1_tools.py`
- Modify: `tests/tools/test_f1_intel_tools.py`
- Modify: `tests/tools/test_cricket_h2h.py`
- Modify: `tests/tools/test_cricket_player_matchup.py`

**Interfaces:**
- Produces: `INVALID_INPUT` envelopes before any chain/model call

- [ ] **Step 1: Add table-driven failing tests**

Cover blank/whitespace/same normalized football matchups, negative bracket/knockout seeds, invalid group whitespace/length, F1 drivers outside 1–99, laps outside 1–200, `current_lap > total_laps`, and cricket H2H/player identifiers over 200 characters or equal after trim+casefold.

Each test must assert the chain mock was not awaited.

- [ ] **Step 2: Verify RED**

```bash
uv run pytest tests/tools/test_football_tools.py tests/tools/test_f1_tools.py tests/tools/test_f1_intel_tools.py tests/tools/test_cricket_h2h.py tests/tools/test_cricket_player_matchup.py -q
```

- [ ] **Step 3: Add local validation only**

Trim inputs before normalization; reject blank, over-limit, and same participants. Validate seeds with:

```python
if seed is not None and not 0 <= seed <= 2**64 - 1:
    return error_envelope(code="INVALID_INPUT", message="seed must be in [0, 2**64 - 1].")
```

Keep validation in each tool; add no shared framework or decorator.

- [ ] **Step 4: Verify and commit**

Run the focused tests and Ruff on changed files, then:

```bash
git commit -m "fix: validate public tool inputs"
```

### Task 9: Implement FIFA-aware ranking and contextual group qualification

**Files:**
- Modify: `src/sportiq/football/models/group_sim.py`
- Modify: `src/sportiq/football/models/bracket_sim.py`
- Modify: `src/sportiq/football/intel_tools.py`
- Modify: `tests/unit/test_group_sim.py`
- Modify: `tests/unit/test_bracket_sim.py`
- Modify: `tests/unit/test_sim_conditioning.py`
- Modify: `tests/tools/test_football_tools.py`

**Interfaces:**
- Produces: `simulate_group_stage(groups, ratings, n_iter, seed, results) -> dict`
- Produces per-team `p_auto_advance`, `p_best_third_advance`, and truthful `p_advance`
- Consumes: the same `simulate_group_once` standings used by bracket simulation

- [ ] **Step 1: Write failing tiebreak tests**

Use deterministic completed `GroupResults` fixtures that create equal overall points but distinct head-to-head records. Assert head-to-head points/GD/goals decide before overall GD, and assert a tie surviving available FIFA fields sets `tiebreak_fallback=True` and uses the higher model rating before RNG.

- [ ] **Step 2: Write failing qualification-stage tests**

Create a 12-group synthetic draw and assert:

```python
out = simulate_group_stage(groups, ratings, n_iter=200, seed=7)
assert sum(row["p_auto_advance"] for row in out["teams"].values()) == pytest.approx(24, abs=0.02)
assert sum(row["p_best_third_advance"] for row in out["teams"].values()) == pytest.approx(8, abs=0.02)
assert sum(row["p_advance"] for row in out["teams"].values()) == pytest.approx(32, abs=0.02)
```

Tool tests must assert one selected group's auto-advance mass is 2 and at least one third-place team can have positive best-third probability.

- [ ] **Step 3: Verify RED**

```bash
uv run pytest tests/unit/test_group_sim.py tests/unit/test_bracket_sim.py tests/unit/test_sim_conditioning.py tests/tools/test_football_tools.py -q
```

- [ ] **Step 4: Implement one ranking path shared by group and bracket sims**

Retain every simulated/fixed match score. Rank equal-point cohorts by FIFA-supported fields: head-to-head points, head-to-head GD, head-to-head GF, overall GD, overall GF. Apply those head-to-head fields once to the equal-points cohort; iterative reapplication to a shrinking tied subset remains an explicit approximation. If still tied, sort by model rating and mark rows that needed this fallback; use RNG only for equal model ratings.

Replace bracket best-third random fallback with rating fallback and count it. Do not claim conduct/FIFA-ranking inputs exist.

- [ ] **Step 5: Implement full group-stage aggregation**

For every iteration, simulate all 12 groups, record positions, select 8 best thirds using the bracket policy, increment auto/best-third/R32 counts, and aggregate average points. Return both all-team rows and `tiebreak_fallbacks`.

Update `football_simulate_group()` to call the full group-stage function, extract only requested group codes, preserve `p_advance`, add the two explicit component fields, and place fallback counts/policy in metadata.

- [ ] **Step 6: Verify invariants and commit**

```bash
uv run pytest tests/unit/test_group_sim.py tests/unit/test_bracket_sim.py tests/unit/test_sim_conditioning.py tests/tools/test_football_tools.py -q
uv run ruff check src/sportiq/football/models/group_sim.py src/sportiq/football/models/bracket_sim.py src/sportiq/football/intel_tools.py
```

Then stage only named files and commit:

```bash
git commit -m "fix(football): model best-third qualification"
```

### Task 10: Make fixture conditioning stage-aware and preserve penalty winners

**Files:**
- Modify: `src/sportiq/football/adapters/api_football.py`
- Modify: `src/sportiq/football/adapters/football_data_org.py`
- Modify: `src/sportiq/football/adapters/openfootball.py`
- Modify: `src/sportiq/football/adapters/static_seed.py`
- Modify: `src/sportiq/football/models/results_state.py`
- Modify: `tests/adapters/test_api_football.py`
- Modify: `tests/adapters/test_football_data_org.py`
- Modify: `tests/adapters/test_openfootball.py`
- Modify: `tests/adapters/test_football_static_seed.py`
- Modify: `tests/unit/test_results_state.py`

**Interfaces:**
- Normalized fixture fields: existing fields plus `match_id`, `stage`, and `winner`
- Produces: group and knockout records that may contain the same team pairing without collision

- [ ] **Step 1: Write failing adapter normalization tests**

For API-Football, assert `fixture.id`, `league.round`, and `teams.*.winner` normalize. For football-data.org, assert `id`, `stage`, and `score.winner` normalize. For openfootball, assert `round` normalizes. Static fixture IDs must be deterministic from group/pair.

- [ ] **Step 2: Write failing result-state regressions**

Create one group match and a later same-pair knockout match with explicit stages; assert both remain, group standings use only the group score, knockout locks the later winner, `matched == 2`, and chronological Elo input contains both. Add a level `PEN` fixture with `winner` and assert it locks; without `winner`, assert it remains dropped.

- [ ] **Step 3: Verify RED**

```bash
uv run pytest tests/adapters/test_api_football.py tests/adapters/test_football_data_org.py tests/adapters/test_openfootball.py tests/adapters/test_football_static_seed.py tests/unit/test_results_state.py -q
```

- [ ] **Step 4: Normalize identity/stage/winner and separate records**

Use provider-native IDs without inventing cross-provider equivalence. Classify explicit group tokens (`GROUP`, `GROUP_STAGE`, `MATCHDAY`, provider group labels) as group; other nonempty stage values as knockout. Only use same-group membership when stage is absent.

Deduplicate provider reports by match ID where present, otherwise `(stage_class, frozenset(pair))`. Build group completed maps and knockout winners separately so stage classes never overwrite each other. Resolve `winner` through the existing team-name/code index.

- [ ] **Step 5: Verify and commit**

Run the focused adapter/result-state tests and Ruff, then:

```bash
git commit -m "fix(football): distinguish rematches by stage"
```

### Task 11: Update branch-local project memory and football documentation

**Files:**
- Modify: `GAPS.md`
- Modify: `PROJECT.md`
- Modify: `docs/hot.md`
- Modify: `docs/index.md`
- Modify: `docs/wiki/tools/football-simulate-group.md`
- Modify: `docs/wiki/tools/football-simulate-bracket.md`
- Modify: `docs/wiki/models/group-sim.md`
- Modify: `docs/wiki/models/bracket-sim.md`
- Modify: `docs/wiki/models/live-conditioning.md`
- Modify: `docs/wiki/chains/football-fixtures-chain.md`
- Modify: `docs/wiki/data-sources/api-football.md`
- Modify: `docs/wiki/data-sources/football-data-org.md`
- Modify: `docs/wiki/data-sources/openfootball.md`
- Modify: `docs/wiki/decisions/0008-football-fallback-strategy.md`
- Modify: `.agents/skills/monte-carlo-bracket/SKILL.md`
- Modify: `.claude/skills/monte-carlo-bracket/SKILL.md`
- Modify: `.claude/rules/fastmcp-conventions.md`
- Modify locally: `docs/log.md` (ignored)

**Interfaces:**
- Consumes: final verified behavior from Tasks 1–10
- Produces: tracked branch memory that distinguishes resolved, partial, and remaining risks

- [ ] **Step 1: Update status memory without erasing history**

Mark GAPS entries resolved/partial with commit/task evidence. Keep these caveats explicit: per-process counters still require max-instances=1; provider peek→fetch race remains; upstream response ceiling still buffers; conduct/FIFA ranking uses an exposed model fallback; no live deployment validation occurred.

Update PROJECT architecture/gotchas and replace stale `docs/hot.md` tool/test/step8 text with the current branch scope.

- [ ] **Step 2: Update football and security wiki pages**

Document truthful group qualification fields, FIFA-supported tiebreak order/fallback, stage-aware fixture normalization, penalty-winner handling, request limits, and atomic counter semantics. Every edited/new wiki page keeps YAML frontmatter and `last_updated: 2026-07-14`.

- [ ] **Step 3: Synchronize both football skills and FastMCP rule**

Both skill copies must say the bracket uses the official R32 template/495-row Annex C allocation; group qualification uses contextual best thirds; and conduct/FIFA-ranking absence is visible. Add the sanctioned `Envelope` exception to `.claude/rules/fastmcp-conventions.md`.

- [ ] **Step 4: Run targeted wiki/doc consistency checks and commit**

```bash
rg -n '^---$|^title:|^type:|^last_updated:' docs/wiki/tools/football-simulate-group.md docs/wiki/tools/football-simulate-bracket.md docs/wiki/models/group-sim.md docs/wiki/models/bracket-sim.md docs/wiki/models/live-conditioning.md docs/wiki/chains/football-fixtures-chain.md docs/wiki/data-sources/api-football.md docs/wiki/data-sources/football-data-org.md docs/wiki/data-sources/openfootball.md docs/wiki/decisions/0008-football-fallback-strategy.md docs/wiki/decisions/0012-hosted-abuse-controls.md
git diff --check -- GAPS.md PROJECT.md docs .agents/skills/monte-carlo-bracket .claude/skills/monte-carlo-bracket .claude/rules/fastmcp-conventions.md
```

Expected: every changed wiki page still exposes YAML frontmatter fields and the diff has no whitespace errors. A repository-wide `/project:update-wiki` lint is not run here because that workflow produces a separate user-triaged punch list beyond this accepted scope.

Stage only tracked memory/docs and commit:

```bash
git commit -m "docs: update hardening and football memory"
```

### Task 12: Final offline verification and branch audit

**Files:**
- Read only: final branch diff and test/build outputs
- Modify locally: `docs/log.md` final operation entry

**Interfaces:**
- Produces: fresh evidence for completion without deployment or main integration

- [ ] **Step 1: Run the complete offline gate**

```bash
bash tests/hooks/test_agent_hooks.sh
uv lock --check
uv run ruff check .
uv run pytest -W error::ResourceWarning
uv run bandit -r src -ll --quiet
uv run python scripts/check_release_build.py
```

Expected: every command exits 0; test count and warnings are recorded exactly.

- [ ] **Step 2: Audit scope and protected files**

```bash
git branch --show-current
git diff main...HEAD --stat
git diff main...HEAD --name-only
git status --short --branch
git log --oneline main..HEAD
```

Expected: branch remains `codex_changes`; no deployment/publish files are executed; `.gitignore` and `review-phase1-cleanup.md` remain unstaged user state.

- [ ] **Step 3: Append the final local journal entry**

Record commits, tests, resolved/partial items, no-live/no-deploy boundaries, and any follow-up. Do not stage the ignored journal.

- [ ] **Step 4: Use `superpowers:finishing-a-development-branch`**

Run the skill, but honor the user's locked choice: keep the work on `codex_changes`; do not merge, push, open a PR, or clean up without a new explicit instruction.
