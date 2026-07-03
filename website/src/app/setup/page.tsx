import type { Metadata } from "next";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Quickstart from "@/components/Quickstart";
import BackgroundCarousel from "@/components/BackgroundCarousel";
import { LINKS } from "@/config/links";

export const metadata: Metadata = {
  title: "Set up SportIQ — connect it to Claude, ChatGPT or Cursor",
  description:
    "Step-by-step setup for SportIQ: add the hosted MCP server as a custom connector in Claude, ChatGPT or Cursor and start asking. All 44 tools are free — no key, no account.",
  alternates: { canonical: "/setup" },
};

const STEPS = [
  {
    n: 1,
    title: "Add the connector",
    body: "Paste the hosted SportIQ URL into your AI client as a custom MCP connector — or run it locally with uvx.",
  },
  {
    n: 2,
    title: "Start asking",
    body: "That's it. All 44 tools — data and full intelligence layer — are live immediately. No key, no account.",
  },
];

const CLIENTS = [
  {
    name: "Claude.ai",
    tag: "Custom connector",
    steps: [
      "Open Settings → Connectors → Add custom connector.",
      "Paste the hosted MCP URL below.",
      "Approve the tools when Claude prompts you.",
    ],
  },
  {
    name: "ChatGPT / Cursor",
    tag: "Any MCP client",
    steps: [
      "Open your client's MCP / connectors settings.",
      "Add a new server pointing at the hosted URL (or the uvx command).",
      "Reload — the SportIQ tools appear in the tool list.",
    ],
  },
  {
    name: "Local (uvx)",
    tag: "Run it yourself",
    steps: [
      "Make sure uv is installed (pipx install uv).",
      "Run uvx sportiq-mcp, or add the JSON config to claude_desktop_config.json.",
      "Optionally set data-source API keys in the env block.",
    ],
  },
];

export default function SetupPage() {
  return (
    <main className="min-h-screen relative selection:bg-action-blue/30 selection:text-black">
      <BackgroundCarousel />
      <Navbar />

      <div className="pt-16">
        {/* Header */}
        <section className="py-20 sm:py-28">
          <div className="max-w-3xl mx-auto px-4 text-center">
            <p className="font-mono text-sm text-action-blue mb-4 uppercase tracking-widest">
              Setup guide
            </p>
            <h1 className="font-oswald text-4xl sm:text-5xl uppercase tracking-tight mb-6 text-white">
              From zero to analyst in 2 steps
            </h1>
            <p className="text-lg text-white/70 leading-relaxed">
              SportIQ runs as a hosted MCP server. Add it as a custom connector in
              Claude, ChatGPT or Cursor and start asking. Two minutes, no build
              step — and every tool is free.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <a
                href={LINKS.sponsors}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-action-blue border border-action-blue rounded-full hover:bg-action-blue hover:text-white transition-colors"
              >
                Sponsor the project &rarr;
              </a>
              <Link
                href="/#pricing"
                className="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-white border border-white/20 rounded-full hover:bg-white/10 transition-colors"
              >
                Support tiers
              </Link>
            </div>
          </div>
        </section>

        {/* 3-step summary */}
        <section className="pb-8">
          <div className="max-w-5xl mx-auto px-4">
            <div className="grid md:grid-cols-2 gap-6">
              {STEPS.map((s) => (
                <div key={s.n} className="glass-panel rounded-2xl p-6">
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center font-oswald text-2xl mb-5 ${
                      s.n === 2
                        ? "bg-action-blue/20 text-action-blue border border-action-blue/30"
                        : "bg-white/10 text-white"
                    }`}
                  >
                    {s.n}
                  </div>
                  <h3 className="font-oswald text-xl uppercase tracking-tight mb-2 text-white">
                    {s.title}
                  </h3>
                  <p className="text-sm text-white/60 leading-relaxed">{s.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Hosted URL callout */}
        <section className="py-12">
          <div className="max-w-3xl mx-auto px-4">
            <div className="glass-panel rounded-2xl p-6 sm:p-8 text-center">
              <p className="text-sm text-white/60 mb-3">
                Hosted MCP endpoint — every tool is free:
              </p>
              <code className="block font-mono text-sm sm:text-base text-action-blue break-all bg-black/30 rounded-xl px-4 py-3 border border-white/10">
                {LINKS.hostedMcp}
              </code>
            </div>
          </div>
        </section>

        {/* Per-client instructions */}
        <section className="py-12">
          <div className="max-w-6xl mx-auto px-4">
            <h2 className="font-oswald text-2xl sm:text-3xl uppercase tracking-tight mb-10 text-center text-white">
              Pick your client
            </h2>
            <div className="grid md:grid-cols-3 gap-6">
              {CLIENTS.map((c) => (
                <div key={c.name} className="glass-panel rounded-2xl p-6">
                  <div className="flex items-baseline justify-between mb-5">
                    <h3 className="font-oswald text-xl uppercase tracking-tight text-white">
                      {c.name}
                    </h3>
                    <span className="font-mono text-[11px] text-action-blue uppercase tracking-wider">
                      {c.tag}
                    </span>
                  </div>
                  <ol className="space-y-4">
                    {c.steps.map((step, i) => (
                      <li key={i} className="flex gap-3 text-sm text-white/70">
                        <span className="font-mono text-action-blue/70 shrink-0">
                          {i + 1}.
                        </span>
                        <span className="leading-relaxed">{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Copyable config (reused) */}
        <Quickstart />

        {/* Screenshot walkthrough */}
        <section className="py-16">
          <div className="max-w-5xl mx-auto px-4">
            <h2 className="font-oswald text-2xl sm:text-3xl uppercase tracking-tight mb-3 text-center text-white">
              The Claude.ai connector flow
            </h2>
            <p className="text-center text-white/50 text-sm mb-12">
              What it looks like, click by click.
            </p>
            <div className="grid sm:grid-cols-2 gap-6">
              {[
                { n: 1, caption: "Settings → Connectors → Add custom connector" },
                { n: 2, caption: "Paste the hosted MCP URL and continue" },
                { n: 3, caption: "Approve the SportIQ tools" },
                { n: 4, caption: "Start asking — all 44 tools are live" },
              ].map((shot) => (
                <figure key={shot.n} className="space-y-3">
                  <div className="relative aspect-[3/2] w-full rounded-xl overflow-hidden glass-panel border-white/20 shadow-2xl">
                    {/* Placeholder until public/step-N.png is added. When the
                        screenshot exists, swap this div for:
                        <Image src={`/step-${shot.n}.png`} alt={shot.caption} fill
                          className="object-cover" sizes="(max-width:768px) 100vw, 600px" /> */}
                    <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                      <span className="font-mono text-white/30 text-sm">
                        step-{shot.n}.png
                      </span>
                    </div>
                  </div>
                  <figcaption className="text-sm text-white/60">
                    <span className="font-mono text-action-blue mr-2">
                      {shot.n}.
                    </span>
                    {shot.caption}
                  </figcaption>
                </figure>
              ))}
            </div>
          </div>
        </section>

        {/* Support callout */}
        <section className="py-12">
          <div className="max-w-3xl mx-auto px-4">
            <div className="glass-panel rounded-2xl p-6 sm:p-8">
              <h3 className="font-oswald text-xl uppercase tracking-tight mb-3 text-white">
                Support SportIQ
              </h3>
              <p className="text-sm text-white/70 leading-relaxed mb-4">
                SportIQ is free — all 44 tools, no key, no account. If it saves
                you time, you can sponsor on GitHub to help cover hosting and
                keep it maintained. Purely voluntary — you get the same
                fully-unlocked server either way.
              </p>
              <a
                href={LINKS.sponsors}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-action-blue border border-action-blue rounded-full hover:bg-action-blue hover:text-white transition-colors"
              >
                Sponsor on GitHub &rarr;
              </a>
            </div>
          </div>
        </section>

        {/* Disclaimer */}
        <section className="pb-20">
          <div className="max-w-3xl mx-auto px-4 text-center">
            <p className="text-xs text-white/40 leading-relaxed">
              SportIQ is an analytics and entertainment tool. Betting outputs
              surface probabilities and value — not guarantees. Not financial
              advice; bet responsibly, and only where it&apos;s legal for you.
            </p>
          </div>
        </section>
      </div>

      <Footer />
    </main>
  );
}
