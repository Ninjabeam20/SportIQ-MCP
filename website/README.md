# SportIQ Marketing Site

This is the front-end codebase for the SportIQ marketing website, an MCP server that turns any AI assistant into a personal sports analyst across football, F1, and cricket. 

Built strictly with **Next.js (App Router)**, **Tailwind CSS v3**, and **TypeScript**, following the Air Design System (frosted glass, energetic accents, sky canvas).

## Tech Stack
- **Framework:** Next.js (App Router)
- **Styling:** Tailwind CSS (custom frosted glass utilities, Air core colors)
- **Typography:** Oswald (Display), Inter (Body/UI), Space Mono (Data/Terminal)
- **Deployment:** Vercel (Statically optimized)

## Quick Start

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Run the development server**
   ```bash
   npm run dev
   ```

3. **Open the site**
   Navigate to [http://localhost:3000](http://localhost:3000) in your browser to see the result.

## Project Structure

- `src/app/page.tsx` — The main single-page application assembly.
- `src/app/layout.tsx` — Global layout, fonts, and full SEO/JSON-LD metadata configuration.
- `src/app/globals.css` — Global CSS including custom `.glass-panel` utilities and Tailwind directives.
- `src/components/` — Individual functional components (Hero, FlagshipCards, PricingSection, etc.).
- `src/config/links.ts` — The single source of truth for all external URLs and payment provider checkouts.
- `public/` — Static assets (logos, screenshots, OpenGraph images).

## Configuration

If you need to update any URLs, download links, or checkout flows, do **not** modify the JSX directly. Edit the `src/config/links.ts` file instead to ensure a single source of truth.

## License

MIT
