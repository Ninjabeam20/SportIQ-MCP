import { LINKS } from "@/config/links";

const ITEMS = [
  {
    sport: "⚽ Football",
    accent: "border-t-sport-football",
    title: "World Cup 2026 what-if",
    body: "football_what_if replays the tournament from any stage and can flip one real knockout result: what if France had beaten Spain? Completed-tournament mode answers from the real results (Spain won the final 1–0 after extra time).",
  },
  {
    sport: "🏎️ F1",
    accent: "border-t-sport-f1",
    title: "Title-race simulator",
    body: "f1_simulate_championship runs a Monte Carlo over the remaining rounds with exact elimination maths. The pit-strategy model now compares the whole remaining race and only recommends legal tyre sequences.",
  },
  {
    sport: "🏏 Cricket",
    accent: "border-t-sport-cricket",
    title: "Official Dream11 T20 scoring",
    body: "Fantasy points follow the official T20 table. IPL squads are generated from Cricsheet, team names and venue strings resolve automatically, and the batter-vs-bowler matchup is now consistent in both directions.",
  },
  {
    sport: "⚙️ Platform",
    accent: "border-t-action-blue",
    title: "Faster, steadier, 46 tools",
    body: "7 MCP resources (draw, team codes, circuits, venues, scoring profile). A cache fix, 30-second tool deadlines, simulations off the event loop, a /healthz route and a smaller server image.",
  },
];

export default function WhatsNew() {
  return (
    <section id="whats-new" className="py-24">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="font-oswald text-3xl sm:text-4xl uppercase tracking-tight mb-4">
            New in <span className="text-action-blue">v0.4.0</span>
          </h2>
          <p className="text-white/70 max-w-xl mx-auto">
            Two new tools, real 2026 results, and accuracy fixes across all three sports. Hosted users get it automatically.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {ITEMS.map((item) => (
            <div
              key={item.title}
              className={`glass-panel rounded-2xl p-6 border-t-2 ${item.accent}`}
            >
              <p className="text-xs font-medium uppercase tracking-wide text-white/60 mb-2">{item.sport}</p>
              <h3 className="font-oswald text-xl uppercase tracking-tight mb-3">{item.title}</h3>
              <p className="text-white/70 text-sm leading-relaxed">{item.body}</p>
            </div>
          ))}
        </div>

        <p className="text-center mt-8 text-sm">
          <a href={LINKS.latestRelease} className="text-action-blue hover:underline">
            Full release notes →
          </a>
        </p>
      </div>
    </section>
  );
}
