---
title: Hosted URL and release-channel drift
type: finding
tags: [cloud-run, docs, release, version, mcp]
sources: [chat]
last_updated: 2026-09-02
related: [[0012-hosted-abuse-controls]], [[0010-trusted-publishing]], [[0011-pro-entitlement-gate]], [[home-server-cutover]], [[product-hosting-arc]]
---

# Hosted URL and release-channel drift

A 2026-08-13 live audit found the **code and Cloud Run process healthy** (766+ tests, revision
`sportiq-mcp-00035-vam` at 100% with `maxScale: 1`) but the **public product surface wrong**.

## Dead connector URL

README, SECURITY.md, PROJECT.md, and `website/src/config/links.ts` advertised

`https://sportiq-mcp-329580761892.us-central1.run.app/mcp`

which does not resolve (DNS NXDOMAIN). Cloud Run `status.url` is

`https://sportiq-mcp-ey2eariulq-uc.a.run.app/mcp`

Live initialize, 44-tool list, `sportiq_health`, and `football_get_groups` succeeded on that
URL. The advertised hostname was updated in-tree on 2026-08-13. This push lands it on
GitHub (and Vercel via `website/src/config/links.ts`). PyPI `uvx sportiq-mcp` stays **0.3.1**
until an owner tags `v0.3.2`. Do **not** swap the advertised URL to
`sportiq.utkarshgupta.org` in this change.

## Three different "0.3.1"s

| Channel | Reality on 2026-08-13 |
|---|---|
| PyPI / `uvx sportiq-mcp` | tag v0.3.1 (2026-07-03), 37 commits behind HEAD |
| Cloud Run | git from 2026-07-14 (hardening), package metadata still 0.3.1 |
| `initialize.serverInfo.version` | MCP SDK version (1.28.1), because FastMCP 1.29 does not forward `version=` |

The working tree is prepared as **0.3.2**: `pyproject.toml` + `server.json`, FastMCP
`mcp._mcp_server.version = __version__`, and `check_release_build.py` fails on `server.json`
drift. Publishing the tag is an operator hard-stop.

## Dockerfile vs lockfile

The image used unpinned `pip install ".[f1]"`, so the host could resolve a different `mcp`
than CI. Dockerfile now copies `uv.lock` and installs with `--frozen`. `mcp` is pinned
`>=1.27.2,<2` because 2.0.0 removes `mcp.server.fastmcp`.

## Related ops (not code)

Leftover public tagged revision URLs (`v2a---`, `candidate---`, …) still initialize. Provider
keys on the public Cloud Run host are plaintext env. Home-server cutover (and later GCP
teardown) is `grok_changes12.md`, not a Cloud Run canary (`grok_changes7.md` is git/PyPI).
See [[home-server-cutover]] and [[product-hosting-arc]].

## Addendum — Task 8 flip (2026-08-30)

The advertised connector is now `https://sportiq.utkarshgupta.org/mcp`.
Cloud Run `ey2eariulq` is rollback only. Do **not** point docs back at
`329580761892` (still NXDOMAIN). GCP teardown still needs `yes, delete GCP`.

## Addendum — v0.3.2 (2026-09-02)

`server.json` now declares `remotes` streamable-http
`https://sportiq.utkarshgupta.org/mcp` next to the PyPI stdio package.
Tag `v0.3.2` is the PyPI + official MCP registry publish.
