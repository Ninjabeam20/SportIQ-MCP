import Link from "next/link";

export default function HowItWorks() {
  return (
    <section id="install" className="py-24 border-y border-white/5 bg-black/40 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="font-oswald text-3xl sm:text-4xl uppercase tracking-tight mb-4">
            From zero to analyst in 3 steps
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-8 mb-16 max-w-5xl mx-auto">
          {/* Step 1 */}
          <div className="text-center">
            <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center font-oswald text-2xl mx-auto mb-6 text-white">1</div>
            <h3 className="font-oswald text-xl uppercase tracking-tight mb-3">Install</h3>
            <p className="text-sm font-mono text-white/60">uvx sportiq-mcp</p>
            <p className="text-sm text-white/60 mt-2">or add to your MCP config</p>
          </div>

          {/* Step 2 */}
          <div className="text-center relative">
            <div className="hidden md:block absolute top-6 left-[-20%] w-[40%] h-px bg-white/10" />
            <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center font-oswald text-2xl mx-auto mb-6 text-white">2</div>
            <div className="hidden md:block absolute top-6 right-[-20%] w-[40%] h-px bg-white/10" />
            <h3 className="font-oswald text-xl uppercase tracking-tight mb-3">Sponsor Pro</h3>
            <p className="text-sm text-white/60">on GitHub Sponsors &rarr;</p>
            <p className="text-sm text-white/60 mt-2">Pro key in your welcome message</p>
          </div>

          {/* Step 3 */}
          <div className="text-center">
            <div className="w-12 h-12 rounded-full bg-action-blue/20 flex items-center justify-center font-oswald text-2xl mx-auto mb-6 text-action-blue border border-action-blue/30">3</div>
            <h3 className="font-oswald text-xl uppercase tracking-tight mb-3">Unlock</h3>
            <p className="text-sm font-mono text-white/60">set SPORTIQ_PRO_KEY</p>
            <p className="text-sm text-white/60 mt-2">in your config. Done.</p>
          </div>
        </div>

        {/* Full guide link */}
        <div className="text-center">
          <Link
            href="/setup"
            className="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-action-blue border border-action-blue rounded-full hover:bg-action-blue hover:text-white transition-colors"
          >
            Full setup guide &rarr;
          </Link>
          <p className="mt-4 text-sm text-white/40">
            Screenshots, per-client steps &amp; the exact config to paste.
          </p>
        </div>
      </div>
    </section>
  );
}
