import { LINKS } from "@/config/links";

export default function ComparisonTable() {
  return (
    <section className="py-24 border-t border-white/5">
      <div className="max-w-5xl mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="font-oswald text-3xl sm:text-4xl uppercase tracking-tight mb-6">
            The data. The decisions. <br />
            <span className="text-action-blue">All of it, free.</span>
          </h2>
        </div>

        <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl">
          <div className="p-8 md:p-12 relative">
            <div className="absolute top-0 right-0 w-32 h-32 bg-action-blue/20 blur-[60px] -z-10 rounded-full" />

            <div className="mb-8">
              <h3 className="font-oswald text-2xl uppercase tracking-tight text-white mb-2">
                Everything&apos;s free
              </h3>
              <p className="text-white/60 text-sm">
                All 44 tools — data layer and full intelligence layer. No key, no account.
              </p>
            </div>

            <ul className="grid md:grid-cols-2 gap-x-12 gap-y-6">
              <li className="flex items-start gap-4 text-white/80">
                <span className="text-white/40 mt-1">✓</span>
                <span>Live scores, fixtures, standings, squads &amp; odds</span>
              </li>
              <li className="flex items-start gap-4 text-white">
                <span className="text-action-blue mt-1">✦</span>
                <span className="font-medium">Monte Carlo bracket &amp; group sims</span>
              </li>
              <li className="flex items-start gap-4 text-white">
                <span className="text-action-blue mt-1">✦</span>
                <span className="font-medium">F1 pit-strategy + tyre degradation</span>
              </li>
              <li className="flex items-start gap-4 text-white">
                <span className="text-action-blue mt-1">✦</span>
                <span className="font-medium">Dream11 optimizer (constraint solver)</span>
              </li>
              <li className="flex items-start gap-4 text-white">
                <span className="text-action-blue mt-1">✦</span>
                <span className="font-medium">+EV value bets — model probability vs the bookmaker line</span>
              </li>
              <li className="flex items-start gap-4 text-white/80">
                <span className="text-white/40 mt-1">✓</span>
                <span>xG models, match predictors &amp; form trends</span>
              </li>
            </ul>

            <p className="mt-10 pt-8 border-t border-white/10 text-sm text-white/60">
              If SportIQ saves you time, you can{" "}
              <a
                href={LINKS.sponsors}
                target="_blank"
                rel="noopener noreferrer"
                className="text-action-blue hover:underline"
              >
                sponsor it on GitHub
              </a>{" "}
              to help cover hosting — purely voluntary, same fully-unlocked server either way.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
