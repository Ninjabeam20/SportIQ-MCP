---
description: File a useful chat finding back into docs/wiki/findings/ so it compounds.
argument-hint: <short-slug-for-the-finding>
---

# /project:file-finding $ARGUMENTS

The Karpathy compounding loop: when a chat answer is useful, file it into the wiki instead of letting it disappear.

The argument is the slug for the new finding file.

## Workflow

1. **Summarise the finding** the user is asking to file, in 3 sentences, and confirm.
2. **Write** `docs/wiki/findings/{slug}.md` with:
   - Frontmatter (`type: finding`, `tags`, `sources: [chat]`, `last_updated`, `related: [[...]]`).
   - 1–2 sentence definition opener.
   - The structured answer.
   - Backlinks to the model / tool / chain pages it relates to.
3. **Update `docs/index.md`** under the Findings section.
4. **Append to `docs/log.md`:** `## [YYYY-MM-DD] finding-filed | {slug}`.
5. **End with Rule #8 format.**

## What you do NOT do

- File generic / unverifiable answers ("Dream11 is fun") — only file content that future-you would want to reference.
- Duplicate an existing finding. Search first; update if the page exists.
