# Testing rules

## No live HTTP in tests, ever

- Adapter tests use `respx` to mock `httpx`. Cassettes live in `tests/fixtures/{source}/`.
- Recording: hit the live API once during development, save the response JSON, commit it. Never re-record automatically.
- If a test starts requiring network, it is broken — not the network.

## Layering

| Layer | Path | What it tests |
| :--- | :--- | :--- |
| `tests/unit/` | Pure model code (PuLP solver, Poisson math, tyre deg fits). No I/O. |
| `tests/adapters/` | A single adapter with respx-mocked HTTP. Asserts the parser handles real upstream shapes. |
| `tests/chains/` | `FallbackChain` behavior. Stub adapters return success / failure / stale; assert order, fallback, stale-serve. |
| `tests/tools/` | End-to-end MCP tool calls. Stub the chain output; assert envelope shape, meta fields, error codes. |

## Conventions

- `pytest-asyncio` `auto` mode (set in `pyproject.toml`). Just write `async def test_...`.
- Fixtures in `conftest.py` provide common chains/adapters/clients.
- One assertion concept per test. Multiple `assert` lines are fine if they verify one outcome.
- Test names: `test_<unit>_<behavior>_<condition>`. Example: `test_fallback_chain_serves_stale_when_all_adapters_fail`.
- `uv run pytest` MUST pass before any commit. Hooks enforce this.
