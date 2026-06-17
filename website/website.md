# SportIQ — Single-Page Website Design & Build Prompt

> **What this file is.** A complete, self-sufficient design + build brief for the SportIQ marketing site.
> Hand this whole file to a build session (or the `frontend-design` skill) and it can ship the site with no extra context.
> Stack is locked: **Next.js (App Router) + Tailwind + TypeScript, deployed to Vercel, fully SEO-optimized.**

---

## 1. Brief & goals

**Subject.** SportIQ — an MCP server that turns any AI assistant (Claude, ChatGPT, Cursor, any MCP client) into a sports analyst across **FIFA World Cup 2026 football, Formula 1, and IPL cricket**. 44 AI-callable tools; the free layer is live data, the paid layer is the intelligence (Monte Carlo bracket sims, F1 pit strategy, Dream11 optimization).

**Audience.** Sports bettors hunting an edge, fantasy (Dream11/FPL) players, F1 strategy nerds, data-driven fans, and devs building sports-AI apps.

**The page's single job.** Convert a visitor to one of two actions:
1. **Install free** → PyPI / `uvx` (low-friction, top of funnel).
2. **Get Pro** → Polar checkout (revenue).
Secondary job: establish credibility — 44 real tools, real models, open-source, MIT.

**Success criteria.** Lighthouse ≥ 95 (SEO / Perf / A11y / Best Practices); converts to Install or Pro above the fold; loads fast on mobile; reads as a premium product, not a betting-spam page.

**Locked decisions.**
- Build: Next.js App Router + Tailwind + TS → **Vercel**, SEO-first.
- Aesthetic: **Air base, energetic sports** (see §3).
- Payments: **provider toggle** above pricing (§4.8).
- Sport order **everywhere**: football → F1 → cricket. Never reorder.

---

## 2. Tech & deploy spec

- **Framework:** Next.js App Router, TypeScript, static-friendly (mostly RSC + a few `"use client"` islands for animation/toggle).
- **Styling:** Tailwind v4 with the Air tokens loaded into `@theme` (§3). No CSS-in-JS.
- **Fonts:** `next/font/google` — Oswald (display), Inter (body/UI), Space Mono (data/mono). Self-host via `next/font` for zero layout shift.
- **Single source of links:** `src/config/links.ts` holds every external URL **and** the per-provider checkout map. Nothing hardcoded in JSX. Placeholders are obvious and swappable:

```ts
// src/config/links.ts
export const LINKS = {
  pypi: "https://pypi.org/project/sportiq-mcp/",
  github: "https://github.com/Ninjabeam20/SportIQ-MCP",
  registry: "https://registry.modelcontextprotocol.io",     // id: io.github.Ninjabeam20/sportiq-mcp
  hostedMcp: "https://sportiq-mcp-329580761892.us-central1.run.app/mcp",
  email: "utkarshgupta885@gmail.com",
} as const;

export type Provider = "polar" | "lemonsqueezy" | "paddle" | "gumroad" | "stripe";
export type Plan = "monthly" | "annual" | "lifetime";

// null = not wired yet → render button as "Coming soon" + disabled.
export const CHECKOUT: Record<Provider, Record<Plan, string | null>> = {
  polar:        { monthly: "https://polar.sh/CHANGE-ME/sportiq-pro?plan=monthly",
                  annual:  "https://polar.sh/CHANGE-ME/sportiq-pro?plan=annual",
                  lifetime:"https://polar.sh/CHANGE-ME/sportiq-pro?plan=lifetime" },
  lemonsqueezy: { monthly: null, annual: null, lifetime: null },
  paddle:       { monthly: null, annual: null, lifetime: null },
  gumroad:      { monthly: null, annual: null, lifetime: null },
  stripe:       { monthly: null, annual: null, lifetime: null },
};
export const DEFAULT_PROVIDER: Provider = "polar";
```

- **Deploy:** Vercel. `next build` clean, no runtime env required for the marketing site.
- **Accessibility floor (non-negotiable):** visible keyboard focus, semantic landmarks, `prefers-reduced-motion` respected, color contrast AA (never put body text directly on `#426188` — use a surface).

---

## 3. Design system

Direction: **Air base, energetic sports.** Keep Air's serene sky-canvas + frosted glass + big compressed type + a *single* blue CTA accent. Inject sport energy through motion, count-ups, and per-sport accents — but those accents live **only inside the three flagship cards and their SVGs**; global chrome stays Air-pure.

### Color tokens (Tailwind `@theme`)

```css
@theme {
  /* Air core (global) */
  --color-sky-canvas: #426188;   /* page background */
  --color-action-blue: #2b7fff;  /* the ONLY interactive/CTA accent */
  --color-midnight-ink: #000000;
  --color-cloud-white: #ffffff;
  --color-charcoal-text: #1b1b1b;
  --color-haze-grey: #f5f5f5;

  /* Per-sport accents — flagship cards + their SVGs ONLY */
  --color-football: #16a34a;  /* pitch emerald */
  --color-f1: #e10600;        /* race red */
  --color-cricket: #f59e0b;   /* IPL saffron */
}
```

Frosted glass recipe (cards, nav, console): `background: rgba(255,255,255,0.10); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.18);`. On light surfaces use Haze Grey instead. **Minimal shadows** — depth comes from blur + surface color, not elevation.

### Type

| Role | Family | Use | Notes |
| :-- | :-- | :-- | :-- |
| Display | **Oswald** (700/900, condensed) | hero headline, section headers, big stats | scoreboard/broadcast energy; Air's Control-Compressed substitute |
| Body / UI | **Inter** (500) | paragraphs, buttons, nav, labels | Air's Control |
| Data / mono | **Space Mono** (400/700) | telemetry numbers, tool names, code, the hero console | the "sports-data terminal" texture; Air's Control-TNT |

Type scale (Air): caption 12 / body 14 / heading-sm 20 / heading 32 / heading-lg 56 / display up to ~120–180 (clamp responsively; Air's 259 is desktop-hero only). Line heights 0.85 (display) / 1.0 / 1.1 / 1.4 / 1.5.

**Deviation from Air (intentional):** drop Air's Dancing Script cursive face. A data/betting product reads wrong in script; Oswald + Space Mono carry the personality instead.

### Spacing / radii

4px base. Spacing scale 4/8/12/16/20/24/32/48/64/80/120. Section gap 48–80. Card padding 20. Radii: inputs 4, buttons/links 8, images 11, cards 14. Outlined-pill CTAs may use a fully-rounded radius for the single primary action (Air's "outlined primary action" guidance).

### Buttons

- **Primary CTA** ("Get SportIQ Pro"): transparent bg, Action-Blue text + 1px Action-Blue border, pill radius, compact padding. Hover: fill Action-Blue → Cloud-White text.
- **Secondary** ("Install free"): ghost — transparent, Cloud-White text + border (on sky canvas) / Charcoal border (on light surface).

### Motion (respect `prefers-reduced-motion: reduce` → freeze to final state)

- Hero console: type-in → resolve → count-up sequence (once on load).
- Scroll-reveal (fade + 12px rise) on each section, staggered.
- Per-card signature loops (see §4.4).
- Stat count-ups on first view (44 tools, 10,000 sims).
- Subtle parallax (≤8px) on ambient background glyphs behind frosted glass.
Keep it orchestrated, not scattered — one clear moment per section.

---

## 4. Section-by-section spec

Order top→bottom. Each block: wireframe + copy + components + motion.

### 4.1 Sticky nav (frosted)

```
┌──────────────────────────────────────────────────────────────┐
│ [▣ mark] SportIQ        Features  Pricing  Install  GitHub     │
│                              [ Install free ]  [ Get Pro → ]   │
└──────────────────────────────────────────────────────────────┘
```
- Frosted, sticks on scroll, subtle bottom hairline.
- Left: **tiny logo (Image #8)** + "SportIQ" wordmark (Oswald).
- Anchors scroll to sections. "Install free" = ghost, "Get Pro →" = outlined-blue pill.
- Mobile: hamburger → slide-down frosted panel.

### 4.2 Hero — the thesis

```
┌──────────────────────────────────────────────────────────────┐
│                                                                │
│   TURN ANY AI INTO YOUR        ┌─ frosted console ──────────┐  │
│   PERSONAL SPORTS ANALYST      │ > Simulate the World Cup    │  │
│   ── (Oswald, huge) ──         │   2026 bracket 10,000×…     │  │
│                                │ ───────────────────────────│  │
│   Monte Carlo World Cup sims,  │  🏆 Brazil      18.4% ▇▇▇▇  │  │
│   F1 pit strategy & Dream11    │  🇫🇷 France      15.1% ▇▇▇   │  │
│   optimization — inside your   │  🇦🇷 Argentina   12.7% ▇▇▇   │  │
│   AI assistant.                │  🏴 England      9.8%  ▇▇    │  │
│                                └────────────────────────────┘  │
│   [ Get SportIQ Pro → ]  [ Install free ]                      │
│   Works with Claude · ChatGPT · Cursor · any MCP client        │
│   · 44 tools · 3 sports                                         │
└──────────────────────────────────────────────────────────────┘
```
- **Headline (Oswald):** "Turn any AI into your personal sports analyst, tipster & fantasy strategist."
- **Sub:** "An MCP server that gives Claude — and any AI assistant — Monte Carlo World Cup simulations, F1 pit-strategy prediction, and Dream11 optimization."
- **Signature element = the ask→answer console** (Space Mono): a real example prompt types in, a divider draws, then the probability rows resolve and **count up** to their %. This *is* the product in one glance. (Numbers are illustrative — label them "illustrative" in a `title`/caption.)
- Primary CTA → `CHECKOUT[provider].monthly` (or scroll to pricing); secondary → `LINKS.pypi`.
- Trust line beneath, mono, muted.
- Ambient bg: slow-drifting sport glyphs (ball / car silhouette / cricket seam) behind a frosted veil; parallax on scroll.
- **Optional:** the existing `docs/assets/SportIQ.mp4` as a muted autoplay loop beside the console on desktop (poster fallback; never the heavy gifs).

### 4.3 Trust strip

"Works with" row: Claude · ChatGPT · Cursor · any MCP client (text or small logos). Then badges: PyPI · MCP Registry · MIT · **44 tools** (count-up). One line on desktop, wraps on mobile.

### 4.4 Three flagship cards — football → F1 → cricket (LOCKED order)

Three frosted cards in a row (stack on mobile). Each uses its **per-sport accent** for the icon, the animated SVG, and a thin top rule — text stays Air-neutral.

| Card | Title | Copy | Signature animation |
| :-- | :-- | :-- | :-- |
| ⚽ football | **Monte Carlo Bracket** | "Simulates the full World Cup 2026 with Poisson xG — 12 groups, top 2 + 8 best thirds into a 32-team knockout, played to a champion thousands of times. Conditioned on live results." | rolling football + probability bars counting up (emerald) |
| 🏎️ F1 | **F1 Pit-Strategy Predictor** | "A tyre-degradation model on real OpenF1 telemetry recommends stop laps and compound sequence — with a confidence score." | racing-line `stroke-dashoffset` draw + tyre-deg curve (race red) |
| 🏏 cricket | **Dream11 Optimizer** | "A PuLP constraint solver builds the optimal fantasy XI — captain & vice-captain — under every credit, role, and team cap." | cricket-ball seam spin + lineup slots filling (saffron) |

Tagline above the row: "Raw data is table stakes. The intelligence layer is the product."

### 4.5 "What you can ask"

Headline: "Stuff that used to take hours and a dozen tabs now takes one sentence." A rotating mono console (or card grid) cycling the example prompts:
- "Simulate the World Cup 2026 bracket 10,000 times — who actually lifts the trophy?"
- "Find me the best value bets in this weekend's fixtures based on real bookmaker odds."
- "Build me the optimal Dream11 team for tonight's IPL match under the credit cap."
- "What's the smartest pit-stop strategy if it rains at the next Grand Prix?"
- "Compare these two F1 drivers' race pace and tell me who's quicker."

### 4.6 Tool explorer (accordion)

Tabs in locked order: **Football (15) · F1 (13) · Cricket (14)** + a small note "+ cross-sport accumulator + health". Each tab is an accordion of its tools, each row tagged `Free` or `Pro`. Flagship tools get a star. (Full list in §6.)

### 4.7 Free vs Pro comparison

Two-column frosted table:

| Free forever | SportIQ Pro |
| :-- | :-- |
| Live scores, fixtures, standings | Monte Carlo bracket & group sims |
| Squads, schedules, results | F1 pit-strategy + tyre degradation |
| Raw odds & data lookups | Dream11 optimizer + value bets |
| ~20 data tools | The full intelligence layer (~22 tools) |

Anchor line: "Free gives you every live score and stat. Pro gives you the decisions — the optimal Dream11 XI, the pit lap, the bracket odds."

### 4.8 Pricing — provider toggle + 3 plans

```
              [ Polar | LemonSqueezy | Paddle | Gumroad | Stripe ]
                          ↑ re-points all 3 buttons via CHECKOUT[]

   ┌ Monthly ───┐   ┌ Annual ★ Best value ┐   ┌ Lifetime ──────┐
   │  $12 /mo   │   │   $79 /yr           │   │  $49 once       │
   │ Cancel     │   │  Save ~45%          │   │ First 50 buyers │
   │ anytime    │   │                     │   │ no subscription │
   │ [ Buy → ]  │   │  [ Buy → ]          │   │ [ Buy → ]       │
   └────────────┘   └─────────────────────┘   └─────────────────┘
   Secure checkout & global tax handled by Polar. Pay once,
   get a license key, paste it into your config.
```
- The toggle (client component) sets active `Provider`; each card button uses `CHECKOUT[provider][plan]`. If `null` → render disabled "Coming soon".
- Annual card is visually emphasized (border highlight, "Best value" ribbon). Lifetime shows scarcity ("First 50 buyers").
- Prices: Monthly **$12/mo**, Annual **$79/yr**, Lifetime **$49 once**.

### 4.9 How it works — 3 steps + screenshot strip

```
  ① Install              ② Buy Pro                ③ Unlock
  uvx sportiq-mcp        checkout on Polar →       set SPORTIQ_PRO_KEY
  or add to MCP config   get your sq_ key by email in your config. Done.

  [ step-1.png ][ step-2.png ][ step-3.png ][ step-4.png ]  ← back-to-back strip
```
A small horizontal strip of back-to-back screenshots showing the connect-to-Claude flow (open config → paste JSON → restart → tools appear / paste `sq_` key). See §5 image manifest.

### 4.10 Quickstart (code)

Tabbed code block with copy buttons:
- **uvx:** `uvx sportiq-mcp`
- **Claude config (JSON):**
```json
{
  "mcpServers": {
    "sportiq": {
      "command": "uvx",
      "args": ["sportiq-mcp"],
      "env": {
        "CRICAPI_KEY": "optional",
        "APIFOOTBALL_KEY": "optional",
        "THEODDS_KEY": "optional"
      }
    }
  }
}
```
- **Unlock Pro:** add `"SPORTIQ_PRO_KEY": "sq_…"` to `env`.
- Note: "No keys? It still runs on free seed + public-source data." + "No install? Add the hosted server as a custom connector: `…run.app/mcp`."

### 4.11 Footer

- Tiny logo + wordmark.
- Columns: **Install** (PyPI) · **Source** (GitHub) · **MCP Registry** · **Contact** (email) · **Legal** (MIT).
- Disclaimer (mono, muted): "SportIQ is an analytics and entertainment tool. It surfaces probabilities and value — not guarantees. Bet responsibly, and only where it's legal for you."
- `© SportIQ 2026 · MIT licensed · Built by Utkarsh Gupta (@Ninjabeam20)`.

---

## 5. SEO spec (Next.js, do not skip)

- **`app/layout.tsx` `metadata`:** title `SportIQ — AI sports intelligence for football, F1 & cricket`; description from the short blurb; `metadataBase`, canonical, `themeColor: #426188`.
- **OpenGraph + Twitter:** `og.png` (1200×630), `summary_large_image`, title/description/url.
- **JSON-LD** (`<script type="application/ld+json">`): `SoftwareApplication` (name, OS-agnostic, free + paid offers), `Product` + three `Offer`s (the plans, prices, `priceCurrency: USD`), and a `FAQPage` (seed 4–5 Qs: "What is an MCP server?", "Which AIs work?", "Is it free?", "How do I unlock Pro?", "Is betting advice guaranteed?").
- **`app/sitemap.ts`** and **`app/robots.ts`** (allow all, point to sitemap).
- Semantic landmarks (`header/main/section/footer`), one `h1`, ordered headings, descriptive `alt` on every image, `aria-label` on icon-only buttons.
- Favicon set via `app/icon.png` + `app/apple-icon.png`.
- Perf: static render, `next/font`, `next/image` for raster, lazy-load below-fold media, compress hero video. Target Lighthouse ≥ 95 across the board.

---

## 6. Tool list (for the explorer accordion)

**Football (15)** — Free: `football_get_groups`, `football_get_fixtures`, `football_get_standings`, `football_get_squad`, `football_get_match_stats`, `football_get_top_scorers`, `football_get_odds`. Pro: `football_xg_model`, `football_match_predictor`, `football_simulate_group`, ★`football_simulate_bracket`, `football_knockout_path`, `football_form_trends`, `football_find_value_bets`, `football_build_accumulator`.

**F1 (13)** — Free: `f1_get_sessions`, `f1_get_drivers`, `f1_get_lap_times`, `f1_get_standings`, `f1_get_race_results`, `f1_get_weather`. Pro: `f1_tyre_degradation`, `f1_undercut_window`, `f1_head_to_head_pace`, `f1_weather_strategy_impact`, `f1_qualifying_analysis`, `f1_race_pace_compare`, ★`f1_predict_pit_strategy`.

**Cricket (14)** — Free: `cricket_get_live_matches`, `cricket_get_scorecard`, `cricket_get_points_table`, `cricket_get_schedule`, `cricket_get_squad`, `cricket_get_live_odds`. Pro: ★`cricket_build_dream11_team`, `cricket_captain_recommendation`, `cricket_differential_picks`, `cricket_player_form_index`, `cricket_get_pitch_report`, `cricket_head_to_head`, `cricket_find_value_bets`, `cricket_player_matchup`.

**Cross-sport (1):** `cross_sport_build_accumulator`. **Diagnostics (1):** `sportiq_health`. **Total = 44** (~20 free / ~22 Pro).

---

## 7. Image manifest — where YOU add images

Only the **two logos** and the **connect-to-Claude screenshots** are required; everything else has an SVG/animation fallback and is optional polish.

| Slot | Path (suggested) | Size | What it shows | Asset / action |
| :-- | :-- | :-- | :-- | :-- |
| Favicon set | `app/favicon.ico`, `app/icon.png` (512), `app/apple-icon.png` (180) | square | brand mark | **Tiny logo — Image #8** |
| Nav + footer mark | `public/logo-mark.(svg\|png)` | ~32px tall | small mark beside wordmark | **Tiny logo — Image #8** |
| Hero / OG wordmark | `public/logo-full.(svg\|png)` | ~240px wide | full lockup (hero optional, OG required) | **Full logo — Image #9** |
| Hero demo video | `public/demo/sportiq.mp4` + `poster.jpg` | ≤1280w | product in action beside the console | use `docs/assets/SportIQ.mp4` (3.3MB) — **not** the 14–30MB gifs |
| Flagship card art ×3 | `public/cards/{football,f1,cricket}.png` | ~800×600 | optional real screenshots; else the SVG animation stands alone | optional — you can drop these later |
| **Connect-to-Claude strip ×3–4** | `public/steps/step-1…4.png` | ~600×400 | open config → paste JSON → restart Claude → tools appear / paste `sq_` key | **you must capture these screenshots** |
| OG / Twitter card | `public/og.png` | 1200×630 | full logo on sky canvas + tagline | derive from **Full logo — Image #9** |
| Decorative ball / car / seam | `public/decor/*` | varies | optional ambient / section dividers | optional — the ball/car images you mentioned |

---

## 8. Copy appendix (verified strings — use verbatim)

- **Tagline:** "AI sports intelligence for football, F1 & cricket — inside your AI assistant."
- **One-liner:** "An MCP server that gives Claude — and any AI assistant — Monte Carlo World Cup simulations, F1 pit-strategy prediction, and Dream11 optimization."
- **Short blurb (meta description):** "SportIQ plugs 44 live sports tools into any AI (Claude, ChatGPT, Cursor): FIFA World Cup 2026 football, Formula 1, and IPL cricket. Ask in plain English — it simulates brackets, finds value bets, optimizes Dream11 teams, and models F1 pit strategy. Free, open-source, installs in seconds via `uvx`."
- **Compatibility line:** "Works with Claude Desktop, Claude Code, ChatGPT, Cursor, and any MCP client."
- **Pro anchor:** "Free gives you every live score and stat. Pro gives you the decisions — the optimal Dream11 XI, the pit lap, the bracket odds."
- **Disclaimer:** see §4.11.

---

## 9. Air deviations (documented on purpose)

1. **Dropped Dancing Script cursive** — a data/betting product reads wrong in script; Oswald + Space Mono carry personality.
2. **Per-sport accent colors added** (emerald / red / saffron) — confined to the three flagship cards + their SVGs; global chrome stays Air-pure with the single Action-Blue CTA accent.
3. **Display size capped** below Air's 259px on non-hero/mobile (clamped) for readability.
Everything else follows Air exactly: sky canvas, frosted glass, minimal shadows, one accent, the radii/spacing scales.
