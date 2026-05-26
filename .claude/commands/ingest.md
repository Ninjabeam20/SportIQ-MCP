---
description: Absorb a file in docs/raw/ into the wiki. Asks for approval before writing.
argument-hint: <path-to-raw-file>
---

# /project:ingest $ARGUMENTS

Process a source file in `docs/raw/` into the wiki. The argument is the path.

## Workflow

1. **Read the raw file.** Do NOT modify `docs/raw/` — it is immutable per `.claude/rules/wiki-conventions.md`.
2. **Surface 3–5 key takeaways to the user in chat.** Be specific; quote numbers, model parameters, API quirks.
3. **Wait for "proceed".** Per CLAUDE.md Rule #1, no writes until acknowledged.
4. **Write** a summary page in `docs/wiki/findings/{slug}.md` OR update an existing model page, depending on the kind of content. Use frontmatter from `.claude/rules/wiki-conventions.md`. Include `sources: [{raw-file-path}]` in frontmatter.
5. **Update `docs/index.md`** with a one-liner if a new page was created.
6. **Append to `docs/log.md`:** `## [YYYY-MM-DD] ingest | "{source title}" ({raw-file-path}). Updated: [[page1]], [[page2]]. Added: [[page3]].`
7. **End with Rule #8 format.**

## What you do NOT do

- Edit anything in `docs/raw/`.
- Write multiple wiki pages from one raw file unless the user says so — concept-per-file applies.
- Skip the takeaways step. The user uses those to spot misinterpretations before they bake in.
