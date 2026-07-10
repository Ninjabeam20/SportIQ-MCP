---
name: "source-command-update-wiki"
description: "Lint pass over docs/wiki/ — contradictions, stale claims, orphans, gaps, missing pages, broken backlinks."
---

# source-command-update-wiki

Use this skill when the user asks to run the migrated source command `update-wiki`.

## Command Template

# /project:update-wiki

Run a lint pass over `docs/wiki/`. The output is a punch list — the user triages; you execute accepted items.

## Checks

1. **Contradictions** between pages (e.g., two pages disagree on CricAPI rate limits).
2. **Stale claims** — page references a past API state contradicted by a more recent ingest.
3. **Orphan pages** — no inbound `[[backlinks]]` from any other page.
4. **Mentioned but missing** — concepts referenced in body text that lack their own page.
5. **Broken backlinks** — `[[page-name]]` that does not resolve.
6. **Data gaps to research** — propose pages to draft (with explicit user confirmation before websearching).
7. **Frontmatter staleness** — `last_updated` >90 days for non-decision pages.

## Output format

A markdown punch list, grouped by check. Each item names files + line numbers + a suggested fix.

```
## Contradictions
- docs/wiki/data-sources/cricapi.md:14 vs docs/wiki/chains/cricket-live-score-chain.md:8 — disagree on daily quota (100 vs 250). Reconcile.

## Orphans
- docs/wiki/models/elo-rating.md — no inbound backlinks. Add from [[football-simulate-bracket]]?
```

## Workflow

1. Run the checks and produce the punch list.
2. Wait for user to triage (accept / reject / defer per item).
3. Execute accepted items as separate edits.
4. **Append to `docs/log.md`:** `## [YYYY-MM-DD] lint | weekly pass. Resolved: N. Deferred: M. New pages drafted: ...`.
5. **End with Rule #8 format.**
