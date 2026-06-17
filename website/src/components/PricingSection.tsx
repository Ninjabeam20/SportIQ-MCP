"use client";

import { useState } from "react";
import { Provider, CHECKOUT, DEFAULT_PROVIDER } from "@/config/links";

export default function PricingSection() {
  const [provider, setProvider] = useState<Provider>(DEFAULT_PROVIDER);

  const providers: { id: Provider; name: string }[] = [
    { id: "polar", name: "Polar" },
    { id: "lemonsqueezy", name: "LemonSqueezy" },
    { id: "paddle", name: "Paddle" },
    { id: "gumroad", name: "Gumroad" },
    { id: "stripe", name: "Stripe" },
  ];

  return (
    <section id="pricing" className="py-24 bg-gradient-to-b from-sky-canvas to-sky-canvas/80">
      <div className="max-w-6xl mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="font-oswald text-4xl sm:text-5xl uppercase tracking-tight mb-8">
            Get SportIQ Pro
          </h2>
          
          <div className="inline-flex items-center bg-black/20 p-1 rounded-full border border-white/10 mb-8 max-w-full overflow-x-auto hide-scrollbar">
            {providers.map((p) => (
              <button
                key={p.id}
                onClick={() => setProvider(p.id)}
                className={`px-6 py-2.5 rounded-full text-sm font-medium transition-all whitespace-nowrap ${
                  provider === p.id
                    ? "bg-white text-charcoal-text shadow-sm"
                    : "text-white/60 hover:text-white hover:bg-white/5"
                }`}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 items-center max-w-5xl mx-auto">
          {/* Monthly Card */}
          <div className="glass-panel rounded-2xl p-8 flex flex-col h-full hover:-translate-y-1 transition-transform">
            <h3 className="font-oswald text-2xl uppercase tracking-tight text-white mb-2">Monthly</h3>
            <div className="mb-6">
              <span className="font-oswald text-5xl font-bold">$12</span>
              <span className="text-white/60"> /mo</span>
            </div>
            <p className="text-sm text-white/70 mb-8 flex-1">Cancel anytime. Full access to the intelligence layer.</p>
            <CheckoutButton url={CHECKOUT[provider].monthly} />
          </div>

          {/* Annual Card */}
          <div className="glass-panel rounded-2xl p-8 flex flex-col h-[105%] border-2 border-action-blue relative shadow-[0_0_40px_rgba(43,127,255,0.15)] z-10 hover:-translate-y-1 transition-transform bg-white/[0.08]">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-action-blue text-white text-xs font-bold uppercase tracking-wider py-1 px-4 rounded-full">
              ★ Best value
            </div>
            <h3 className="font-oswald text-2xl uppercase tracking-tight text-white mb-2 mt-2">Annual</h3>
            <div className="mb-2">
              <span className="font-oswald text-5xl font-bold">$79</span>
              <span className="text-white/60"> /yr</span>
            </div>
            <div className="text-sport-football text-sm font-medium mb-4">Save ~45%</div>
            <p className="text-sm text-white/70 mb-8 flex-1">A full year of intelligence. Perfect for the season.</p>
            <CheckoutButton url={CHECKOUT[provider].annual} primary />
          </div>

          {/* Lifetime Card */}
          <div className="glass-panel rounded-2xl p-8 flex flex-col h-full hover:-translate-y-1 transition-transform">
            <h3 className="font-oswald text-2xl uppercase tracking-tight text-white mb-2">Lifetime</h3>
            <div className="mb-6">
              <span className="font-oswald text-5xl font-bold">$49</span>
              <span className="text-white/60"> once</span>
            </div>
            <p className="text-sm text-white/70 mb-2">First 50 buyers no subscription.</p>
            <p className="text-xs text-white/50 mb-8 flex-1">Own the current major version forever.</p>
            <CheckoutButton url={CHECKOUT[provider].lifetime} />
          </div>
        </div>

        <div className="mt-16 text-center max-w-2xl mx-auto">
          <p className="text-sm text-white/60 leading-relaxed">
            Secure checkout & global tax handled by Polar. <br className="hidden sm:block" />
            Pay once, get a license key, paste it into your config.
          </p>
        </div>
      </div>
    </section>
  );
}

function CheckoutButton({ url, primary = false }: { url: string | null; primary?: boolean }) {
  if (!url) {
    return (
      <button disabled className="w-full py-4 rounded-full font-medium text-white/30 bg-white/5 border border-white/5 cursor-not-allowed">
        Coming soon
      </button>
    );
  }

  return (
    <a
      href={url}
      className={`w-full py-4 rounded-full font-medium text-center transition-colors ${
        primary
          ? "bg-action-blue text-white hover:bg-action-blue/90"
          : "text-action-blue border border-action-blue hover:bg-action-blue hover:text-white"
      }`}
    >
      Buy &rarr;
    </a>
  );
}
