---
description: Scaffold a new MCP tool end-to-end (tool + adapter + chain wiring + test + wiki page).
argument-hint: <sport> <tool_name>
---

# /project:add-tool $ARGUMENTS

Scaffold a complete tool. The arguments are `<sport> <tool_name>` — for example `cricket cricket_get_top_scorers`.

## Steps

1. **Confirm intent.** Read the user's intent in one paragraph back to them. Stop and ask if ambiguous.
2. **Add the tool function** in `src/sportiq/{sport}/tools.py`:
   - `@mcp.tool()` decorator.
   - Full type hints; docstring with `Args:` block.
   - Body: validate → call chain → wrap with `tool_response()` / `error_envelope()`.
3. **Wire the chain.** If a chain for this data category exists, reuse. Otherwise add to `src/sportiq/{sport}/chains.py` and update `.claude/rules/caching-policy.md` with the new TTL row.
4. **Add test file** `tests/tools/test_{tool_name}.py`:
   - Stub the chain to return both success and failure cases.
   - Assert envelope shape, meta fields, and error codes.
5. **Add wiki page** `docs/wiki/tools/{tool-name-kebab}.md` with frontmatter (`type: tool`).
6. **Update `docs/index.md`** with a one-liner under the Tools section.
7. **Append to `docs/log.md`:** `## [YYYY-MM-DD] tool-added | {tool_name}`.
8. **Run `uv run pytest tests/tools/test_{tool_name}.py`** and report results.
9. **End with Rule #8 format.**

## What you do NOT do

- Touch unrelated tools or chains.
- Hit live APIs to "see what the data looks like" — ask the user for a sample.
- Skip the wiki page or log entry.
