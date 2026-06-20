export default function ComparisonTable() {
  return (
    <section className="py-24 border-t border-white/5">
      <div className="max-w-5xl mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="font-oswald text-3xl sm:text-4xl uppercase tracking-tight mb-6">
            Free gives you the data. <br />
            <span className="text-action-blue">Pro gives you the decisions.</span>
          </h2>
        </div>

        <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl">
          <div className="grid md:grid-cols-2">
            {/* Free Column */}
            <div className="p-8 md:p-12 border-b md:border-b-0 md:border-r border-white/10 bg-white/5">
              <div className="mb-8">
                <h3 className="font-oswald text-2xl uppercase tracking-tight text-white mb-2">Free forever</h3>
                <p className="text-white/60 text-sm">~20 data tools</p>
              </div>
              
              <ul className="space-y-6">
                <li className="flex items-start gap-4 text-white/80">
                  <span className="text-white/40 mt-1">✓</span>
                  <span>Live scores, fixtures, standings</span>
                </li>
                <li className="flex items-start gap-4 text-white/80">
                  <span className="text-white/40 mt-1">✓</span>
                  <span>Squads, schedules, results</span>
                </li>
                <li className="flex items-start gap-4 text-white/80">
                  <span className="text-white/40 mt-1">✓</span>
                  <span>Raw odds & data lookups</span>
                </li>
              </ul>
            </div>

            {/* Pro Column */}
            <div className="p-8 md:p-12 bg-action-blue/5 relative">
              <div className="absolute top-0 right-0 w-32 h-32 bg-action-blue/20 blur-[60px] -z-10 rounded-full" />
              
              <div className="mb-8">
                <h3 className="font-oswald text-2xl uppercase tracking-tight text-action-blue mb-2">SportIQ Pro</h3>
                <p className="text-white/60 text-sm">The full intelligence layer (24 tools)</p>
              </div>

              <ul className="space-y-6">
                <li className="flex items-start gap-4 text-white">
                  <span className="text-action-blue mt-1">✦</span>
                  <span className="font-medium">Monte Carlo bracket & group sims</span>
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
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
