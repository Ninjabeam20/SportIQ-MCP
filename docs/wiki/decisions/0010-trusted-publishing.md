---
title: ADR-0010 PyPI Trusted Publishing (OIDC)
type: decision
tags: [release, security, pypi]
last_updated: 2026-09-25
related: []
---

# ADR-0010 — PyPI Trusted Publishing (OIDC)

## Status: Implemented in the release workflow; PyPI account settings need an external check

## Context

Long-lived PyPI API tokens committed to CI secrets are a supply-chain risk.
PyPI supports Trusted Publishing via OIDC — GitHub Actions proves identity via
a short-lived JWT, no stored token required.

## Decision

Use Trusted Publishing for all PyPI releases. `.github/workflows/release.yml`
uses `pypa/gh-action-pypi-publish` with OIDC and no explicit token; the project
documents a published 0.3.2 release. The repo cannot prove the current PyPI
publisher binding or GitHub secret settings; check those in their UIs before
claiming the one-time setup is complete.

## External settings to verify before the next release

1. Go to https://pypi.org/manage/project/sportiq-mcp/settings/publishing/
2. Confirm the "GitHub Actions" publisher is present:
   - Owner: Ninjabeam20
   - Repository: SportIQ-MCP
   - Workflow name: release.yml
   - Environment: `pypi` (must match `release.yml`)
3. Confirm there is no unused `PYPI_TOKEN` secret in GitHub repository secrets.

## Consequences

- No long-lived token stored anywhere.
- Release workflow must run from the `main` branch (or a tagged commit).
- The `check_release_build.py` script verifies artifact contents on every CI run.
