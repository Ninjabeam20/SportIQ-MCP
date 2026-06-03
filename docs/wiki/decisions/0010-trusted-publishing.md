---
title: ADR-0010 PyPI Trusted Publishing (OIDC)
type: decision
tags: [release, security, pypi]
last_updated: 2026-06-03
related: [[release]]
---

# ADR-0010 — PyPI Trusted Publishing (OIDC)

## Status: Pending operator action

## Context

Long-lived PyPI API tokens committed to CI secrets are a supply-chain risk.
PyPI supports Trusted Publishing via OIDC — GitHub Actions proves identity via
a short-lived JWT, no stored token required.

## Decision

Use Trusted Publishing for all PyPI releases. The code side is ready (the
release workflow will use `pypa/gh-action-pypi-publish` with no explicit
token). The OIDC trust link requires a one-time manual step in PyPI's web UI.

## Manual setup (one-time)

1. Go to https://pypi.org/manage/project/sportiq-mcp/settings/publishing/
2. Add a "GitHub Actions" publisher:
   - Owner: Ninjabeam20
   - Repository: SportIQ-MCP
   - Workflow name: release.yml
   - Environment: (leave blank or use `pypi`)
3. Remove the old `PYPI_TOKEN` secret from GitHub repository secrets.

## Consequences

- No long-lived token stored anywhere.
- Release workflow must run from the `main` branch (or a tagged commit).
- The `check_release_build.py` script verifies artifact contents on every CI run.
