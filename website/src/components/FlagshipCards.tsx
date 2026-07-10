"use client";

export default function FlagshipCards() {
  return (
    <section id="features" className="py-24 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="font-oswald text-3xl sm:text-4xl uppercase tracking-tight mb-4">
            Raw data is table stakes. <br />
            <span className="text-action-blue">The intelligence layer is the product.</span>
          </h2>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Football Card */}
          <div className="glass-panel rounded-2xl p-8 relative overflow-hidden group border-t-2 border-t-sport-football hover:bg-white/[0.12] transition-colors">
            <div className="mb-6 flex items-center justify-between">
              <span className="text-3xl">⚽</span>
              <div className="w-10 h-10 rounded-full bg-sport-football/10 flex items-center justify-center text-sport-football">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
            </div>
            <h3 className="font-oswald text-2xl uppercase tracking-tight mb-3">Monte Carlo Bracket</h3>
            <p className="text-white/70 text-sm leading-relaxed mb-8 h-24">
              Simulates the full World Cup 2026 with Poisson xG — 12 groups, top 2 + 8 best thirds into a 32-team knockout, played to a champion thousands of times. Conditioned on live results.
            </p>
            
            {/* Signature Animation */}
            <div className="h-32 rounded-xl bg-black/20 border border-white/5 p-4 flex flex-col justify-end gap-2 relative overflow-hidden">
              <div className="absolute top-4 right-4 flex gap-1">
                <div className="w-2 h-2 rounded-full bg-sport-football animate-pulse" />
                <div className="w-2 h-2 rounded-full bg-sport-football/50" />
                <div className="w-2 h-2 rounded-full bg-sport-football/20" />
              </div>
              <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-sport-football w-0 group-hover:w-[85%] transition-all duration-1000 ease-out" />
              </div>
              <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-white/40 w-0 group-hover:w-[60%] transition-all duration-1000 delay-100 ease-out" />
              </div>
              <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-white/20 w-0 group-hover:w-[35%] transition-all duration-1000 delay-200 ease-out" />
              </div>
            </div>
          </div>

          {/* F1 Card */}
          <div className="glass-panel rounded-2xl p-8 relative overflow-hidden group border-t-2 border-t-sport-f1 hover:bg-white/[0.12] transition-colors">
            <div className="mb-6 flex items-center justify-between">
              <span className="text-3xl">🏎️</span>
              <div className="w-10 h-10 rounded-full bg-sport-f1/10 flex items-center justify-center text-sport-f1">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <h3 className="font-oswald text-2xl uppercase tracking-tight mb-3">F1 Pit-Strategy Predictor</h3>
            <p className="text-white/70 text-sm leading-relaxed mb-8 h-24">
              A tyre-degradation model on real OpenF1 telemetry recommends stop laps and compound sequence — with a confidence score.
            </p>
            
            {/* Signature Animation */}
            <div className="h-32 rounded-xl bg-black/20 border border-white/5 p-4 relative overflow-hidden flex items-end">
              <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                <path 
                  d="M 0,100 C 50,100 100,50 150,80 C 200,110 250,20 300,40" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  className="text-white/10"
                />
                <path 
                  d="M 0,100 C 50,100 100,50 150,80 C 200,110 250,20 300,40" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  className="text-sport-f1"
                  strokeDasharray="400"
                  strokeDashoffset="400"
                  style={{ transition: 'stroke-dashoffset 1.5s ease-out' }}
                />
                <style>{`
                  .group:hover path.text-sport-f1 {
                    stroke-dashoffset: 0;
                  }
                `}</style>
              </svg>
              <div className="relative z-10 w-full flex justify-between text-xs font-mono text-white/50">
                <span>Lap 15</span>
                <span className="text-sport-f1 font-bold animate-pulse">BOX BOX</span>
                <span>Lap 35</span>
              </div>
            </div>
          </div>

          {/* Cricket Card */}
          <div className="glass-panel rounded-2xl p-8 relative overflow-hidden group border-t-2 border-t-sport-cricket hover:bg-white/[0.12] transition-colors">
            <div className="mb-6 flex items-center justify-between">
              <span className="text-3xl">🏏</span>
              <div className="w-10 h-10 rounded-full bg-sport-cricket/10 flex items-center justify-center text-sport-cricket">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
              </div>
            </div>
            <h3 className="font-oswald text-2xl uppercase tracking-tight mb-3">Dream11 Optimizer</h3>
            <p className="text-white/70 text-sm leading-relaxed mb-8 h-24">
              A PuLP constraint solver builds the optimal fantasy XI — captain & vice-captain — under every credit, role, and team cap.
            </p>
            
            {/* Signature Animation */}
            <div className="h-32 rounded-xl bg-black/20 border border-white/5 p-4 relative overflow-hidden">
              <div className="grid grid-cols-5 gap-2 h-full">
                {[...Array(11)].map((_, i) => (
                  <div key={i} className="flex flex-col items-center justify-end gap-1 group-hover:-translate-y-1 transition-transform" style={{ transitionDelay: `${i * 50}ms` }}>
                    <div className={`w-full rounded-sm ${i === 0 ? 'bg-sport-cricket h-[80%]' : i === 1 ? 'bg-white/60 h-[70%]' : 'bg-white/20 h-[50%]'}`} />
                  </div>
                ))}
              </div>
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent pointer-events-none" />
              <div className="absolute bottom-2 w-full text-center text-xs font-mono text-sport-cricket opacity-0 group-hover:opacity-100 transition-opacity delay-500">
                XI GENERATED
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
