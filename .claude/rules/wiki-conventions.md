# Wiki conventions

Every page in `docs/wiki/` has YAML frontmatter. No exceptions.

## Frontmatter schema

```yaml
---
title: Dream11 Scoring Table
type: model | tool | data-source | chain | decision | finding
tags: [cricket, scoring, ipl]
sources: [cricapi, dream11-official-rules]
last_updated: 2026-05-26
related: [[cricket-build-dream11-team]], [[dream11-solver]]
---
```

- `title` — human-readable; mirrors the H1.
- `type` — one of the six values above.
- `tags` — kebab-case, lowercased.
- `sources` — wiki page slugs or `docs/raw/` filenames the content was derived from.
- `last_updated` — ISO date. The `/project:update-wiki` lint flags pages >90 days old (except `type: decision`).
- `related` — Obsidian-style `[[backlinks]]`. Link liberally.

## Body rules

- One concept per file. If the page exceeds ~400 lines, split.
- Body opens with a 1–2 sentence definition. The `docs/index.md` one-liner mirrors this opener.
- Backlinks via `[[page-name]]` in prose. Obsidian graph view renders them for free.
- Link out; do not duplicate content across pages.

## Ownership (Karpathy three-layer)

- `docs/raw/` — **immutable**. User drops sources here. LLM reads but NEVER modifies.
- `docs/wiki/` — **LLM-owned**. LLM creates and updates pages. User reads and directs.
- `CLAUDE.md` + `.claude/` — **co-evolved**. Both edit.

## When to write a new page

- After a non-trivial finding in chat (`/project:file-finding`).
- After ingesting a `docs/raw/` source (`/project:ingest`).
- When adding a tool, adapter, model, chain, or decision (handled by `/project:add-tool` and `/project:add-adapter`).
