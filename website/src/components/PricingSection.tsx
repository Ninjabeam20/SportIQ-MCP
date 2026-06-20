import { LINKS, PRICING, Tier } from "@/config/links";

export default function PricingSection() {
  return (
    <section id="pricing" className="py-24 bg-gradient-to-b from-sky-canvas to-sky-canvas/80">
      <div className="max-w-6xl mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="font-oswald text-4xl sm:text-5xl uppercase tracking-tight mb-4">
            Get SportIQ Pro
          </h2>
          <p className="text-white/70 max-w-2xl mx-auto">
            One key unlocks all 24 intelligence tools — Monte Carlo World Cup sims,
            F1 pit strategy, Dream11 optimizers, and model-vs-market value bets.
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 items-center max-w-5xl mx-auto">
          {PRICING.map((tier) => (
            <PriceCard key={tier.plan} tier={tier} />
          ))}
        </div>

        <div className="mt-16 text-center max-w-2xl mx-auto space-y-2">
          <p className="text-sm text-white/60 leading-relaxed">
            Secure checkout via <strong className="text-white/80">GitHub Sponsors</strong>.
            Sponsor at Pro or Lifetime → your Pro key is in the welcome message →
            paste it into your config as <code className="font-mono text-action-blue">SPORTIQ_PRO_KEY</code>.
          </p>
          <p className="text-xs text-white/40">
            Analytics &amp; entertainment only — not financial advice. Bet responsibly.
          </p>
        </div>
      </div>
    </section>
  );
}

function PriceCard({ tier }: { tier: Tier }) {
  const featured = tier.featured;

  return (
    <div
      className={`glass-panel rounded-2xl p-8 flex flex-col relative hover:-translate-y-1 transition-transform ${
        featured
          ? "h-[105%] border-2 border-action-blue shadow-[0_0_40px_rgba(0,240,255,0.15)] z-10 bg-white/[0.08]"
          : "h-full"
      }`}
    >
      {tier.badge && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-action-blue text-white text-xs font-bold uppercase tracking-wider py-1 px-4 rounded-full whitespace-nowrap">
          {tier.badge}
        </div>
      )}
      <h3 className={`font-oswald text-2xl uppercase tracking-tight text-white mb-2 ${featured ? "mt-2" : ""}`}>
        {tier.name}
      </h3>
      <div className="mb-4">
        <span className="font-oswald text-5xl font-bold">{tier.price}</span>
        <span className="text-white/60"> {tier.cadence}</span>
      </div>
      <p className="text-sm text-white/70 mb-8 flex-1">{tier.tagline}</p>
      <a
        href={LINKS.sponsors}
        target="_blank"
        rel="noopener noreferrer"
        className={`w-full py-4 rounded-full font-medium text-center transition-colors ${
          featured
            ? "bg-action-blue text-white hover:bg-action-blue/90"
            : "text-action-blue border border-action-blue hover:bg-action-blue hover:text-white"
        }`}
      >
        Sponsor &amp; unlock &rarr;
      </a>
    </div>
  );
}
