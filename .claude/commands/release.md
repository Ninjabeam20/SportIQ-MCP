---
description: Version bump → build → publish to PyPI. Requires explicit "yes" before publishing.
argument-hint: <major|minor|patch>
---

# /project:release $ARGUMENTS

Cut a release. Argument is the semver bump kind.

## Workflow

1. **Read** `pyproject.toml` current version.
2. **Compute** new version per the bump kind.
3. **Show the user** the new version + the changelog (from `git log` since the last tag).
4. **STOP. Wait for explicit "yes".** Per CLAUDE.md Rule #7, publishing is irreversible.
5. After approval:
   - `uv run pytest` (must pass).
   - `uv run ruff check .` (must pass).
   - Bump version in `pyproject.toml` **and** `server.json` (MCP registry; `__init__.__version__` is dynamic — leave it).
   - `uv lock` and `uv run python scripts/check_release_build.py` (fails if `server.json` drifts or the sdist allowlist leaks).
   - `git commit -m "release: vX.Y.Z"`.
   - `git tag vX.Y.Z`.
   - `git push && git push --tags` (only after explicit confirmation).
   - The `release.yml` workflow runs lint + tests + coverage + the release-build check on tag push, then publishes to PyPI via Trusted Publishing.
6. **Append to `docs/log.md`:** `## [YYYY-MM-DD] release | vX.Y.Z to PyPI. {tools added | bugfixes | breaking changes}.`
7. **End with Rule #8 format.**

## Hard rules

- NEVER publish without `uv run pytest` passing.
- NEVER force-push tags.
- NEVER bump version in a branch other than `main`.
