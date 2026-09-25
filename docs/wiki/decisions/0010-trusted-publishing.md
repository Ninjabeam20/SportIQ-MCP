---
title: ADR-0010 PyPI Trusted Publishing (OIDC)
type: decision
tags: [release, security, pypi]
last_updated: 2026-09-25
related: []
---

# ADR-0010 — PyPI Trusted Publishing (OIDC)

## Status: Published successfully; current PyPI account binding is not visible without login

## Context

Long-lived PyPI API tokens committed to CI secrets are a supply-chain risk.
PyPI supports Trusted Publishing via OIDC — GitHub Actions proves identity via
a short-lived JWT, no stored token required.

## Decision

Use Trusted Publishing for all PyPI releases. `.github/workflows/release.yml`
uses `pypa/gh-action-pypi-publish` with OIDC and no explicit token. The
`v0.3.2` release workflow's "Publish to PyPI" step succeeded on 2026-09-02.
GitHub listed no repository secrets on 2026-09-25, including no `PYPI_TOKEN`.
These checks show the setup worked for that release; the current PyPI publisher
binding is private and needs an authenticated PyPI account check.

## External settings to verify before the next release

1. Go to https://pypi.org/manage/project/sportiq-mcp/settings/publishing/
2. Confirm the "GitHub Actions" publisher is present:
   - Owner: Ninjabeam20
   - Repository: SportIQ-MCP
   - Workflow name: release.yml
   - Environment: `pypi` (must match `release.yml`)
3. GitHub repository secrets were empty on 2026-09-25; recheck if credentials are added later.

## Consequences

- No long-lived token stored anywhere.
- Release workflow must run from the `main` branch (or a tagged commit).
- The `check_release_build.py` script verifies artifact contents on every CI run.
