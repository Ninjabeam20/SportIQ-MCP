# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The marketing/landing website for **SportIQ**. This directory (`website/`, inside the sportiq-mcp monorepo) is the public site only — the SportIQ product itself is the MCP server in the rest of the repo. The site ships independently: excluded from the PyPI sdist and the Cloud Run image, built by its own CI workflow (`.github/workflows/website.yml`), and deployed via Vercel with Root Directory = `website`.

**SportIQ** is a hosted **MCP (Model Context Protocol) server** that gives Claude — and any MCP client (ChatGPT, Cursor, etc.) — live sports analytics across **football, F1, and cricket**: live scores, schedules, squads, standings, odds, value-bet detection, fantasy/Dream11 team building, and predictive models (xG, pit strategy, match predictor, Monte Carlo bracket simulation, etc.).

- It is consumed as a **custom connector in Claude.ai** (Settings → Connectors → Add custom connector → paste the MCP URL), not run locally from this repo.
- Production MCP endpoint: `https://sportiq-mcp-329580761892.us-central1.run.app/mcp` (Google Cloud Run). Source of truth for this and all other external URLs is `src/config/links.ts`.
- The site's job is to market SportIQ and walk users through adding it as a connector.

## Commands

```bash
npm run dev      # local dev server at http://localhost:3000
npm run build    # production build (statically optimized)
npm run start    # serve the production build
npm run lint     # next lint (ESLint)
```

There are no tests.

## Architecture

Next.js 15 App Router + React 19 + Tailwind v3 + TypeScript. Import alias `@/` maps to `src/`.

- **`src/app/page.tsx`** is the entire site: a single `<main>` that stacks section components in render order. Adding/reordering a section happens here. Each section component is self-contained and owns its own copy, layout, and (often hardcoded) data.
- **`src/app/layout.tsx`** owns the `<html>` shell: `next/font` loading (Oswald=display, Inter=body, Space Mono=data/terminal, exposed as CSS variables), all SEO `metadata`, and two inline JSON-LD `<script>` blocks (SoftwareApplication offers + FAQPage). Pricing numbers and FAQ answers are duplicated here as structured data — keep them in sync with the visible components.
- **`src/components/`** — one file per section (Hero, FlagshipCards, PricingSection, ToolExplorer, etc.). Interactive ones are `"use client"`; the rest are server components.
- **`BackgroundCarousel.tsx`** is a fixed full-viewport (`z-[-1]`) image crossfade behind everything; its images use `unoptimized` (local artifacts).

## Conventions that matter

- **All external URLs and pricing live in `src/config/links.ts`** — never hardcode a URL, download link, or price in JSX. **Everything is free**: all 44 tools, no key, no account, nothing gated. The `PRICING` array (Supporter $5/mo, Pro $10/mo, Lifetime $49 once) is **voluntary GitHub Sponsors tiers** (`LINKS.sponsors`) that `PricingSection.tsx` maps over — the tier names are legacy labels, not unlocks; never reintroduce "Pro unlocks X" copy. Note: the JSON-LD `offers` prices and the "Is it free?" / sponsor FAQ answers in `layout.tsx` duplicate these numbers — keep them in sync.
- **Styling is the "Air Design System"**: dark canvas + frosted glass + neon accent. Use the custom Tailwind tokens in `tailwind.config.ts` (`sky-canvas`, `action-blue`, `sport-{football,f1,cricket}`, etc.) and the `.glass-panel` / `.glass-panel-light` utilities in `globals.css` rather than ad-hoc colors. Use `font-oswald` for headings (uppercase), `font-inter` for body, `font-mono` for tool names / terminal text.
- The MCP tool catalog shown in `ToolExplorer.tsx` is a hardcoded list of `Tool` objects (`{ name, isFlagship? }`, grouped per sport — no Free/Pro tags since the free reframe) — update it there when the server's tool surface changes.
- The site references live betting/odds output. Any betting/odds copy should carry the framing shown in the product: **"Not financial advice — bet responsibly."**
- Reuse the existing image assets (`logo-full.png`, `logo-mark.png`, the `step-1.png`–`step-4.png` connector walkthrough) as source material rather than regenerating them.

## Standing instructions (how to work in this repo)

Durable working preferences — follow them every session unless the user overrides.

- **Sport ordering**: order sports **football → F1 → cricket** everywhere (copy, sections, lists). (Flipped from cricket-first on 2026-06-06.)
- **Commit messages**: Conventional Commits style (`feat:`, `fix:`, etc.) with a bulleted body and a `Co-Authored-By` tag.
- **Push discipline**: never auto-push. Wait for explicit per-session sign-off before pushing.
- **Plan-then-execute**: for multi-step work, write a detailed step-by-step plan file first, then execute it.
- **Step docs are local-only**: `step*.md` files are working notes — never commit them.
