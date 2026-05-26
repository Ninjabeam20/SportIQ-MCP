---
description: Add a new data-source adapter to an existing FallbackChain.
argument-hint: <sport> <chain_name> <adapter_name>
---

# /project:add-adapter $ARGUMENTS

Add an adapter to a chain. Arguments: `<sport> <chain_name> <adapter_name>`. Example: `cricket live_score espncricinfo_scraper`.

## Steps

1. **Read** `.claude/rules/fallback-contract.md` and `.claude/rules/api-budgets.md` first.
2. **Confirm the adapter's order in the chain** with the user — chains are ordered, position matters.
3. **Write the adapter** in `src/sportiq/{sport}/adapters/{adapter_name}.py`:
   - Implements the `Adapter` protocol (`name`, `async fetch(**kwargs)`, `async healthcheck()`).
   - Uses `core.http.client()` (already wired with `tenacity`).
   - Raises a typed error on failure — never returns `None`.
4. **Register** the adapter in the chain in `src/sportiq/{sport}/chains.py` at the user-confirmed position.
5. **Add a respx-mocked test** in `tests/adapters/test_{adapter_name}.py`. Cassettes in `tests/fixtures/{adapter_name}/`.
6. **Add wiki page** `docs/wiki/data-sources/{adapter-name-kebab}.md` (`type: data-source`) documenting:
   - Auth model · rate caps · known quirks · response shape · what to do when it's down.
7. **Update** `.claude/rules/api-budgets.md` with the new source's quota row.
8. **Update** `docs/wiki/chains/{chain-name}.md` to show the new adapter in the order.
9. **Append to `docs/log.md`:** `## [YYYY-MM-DD] adapter-added | {adapter_name} → {chain_name}`.
10. **Run `uv run pytest tests/adapters/test_{adapter_name}.py`** and report.
11. **End with Rule #8 format.**
