"use client";

import { useState, useEffect } from "react";

const PROMPTS = [
  "Simulate the World Cup 2026 bracket 10,000 times — who actually lifts the trophy?",
  "Find me the best value bets in this weekend's fixtures based on real bookmaker odds.",
  "Build me the optimal Dream11 team for tonight's IPL match under the credit cap.",
  "What's the smartest pit-stop strategy if it rains at the next Grand Prix?",
  "Compare these two F1 drivers' race pace and tell me who's quicker.",
];

export default function FeaturePrompts() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveIndex((current) => (current + 1) % PROMPTS.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  return (
    <section className="py-20 border-y border-white/5 bg-black/40 backdrop-blur-md">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <h2 className="font-oswald text-2xl sm:text-3xl uppercase tracking-tight mb-12 text-white/90">
          Stuff that used to take hours and a dozen tabs <br/>
          <span className="text-white">now takes one sentence.</span>
        </h2>

        <div className="glass-panel p-6 sm:p-8 rounded-2xl relative min-h-[140px] flex items-center justify-center">
          {PROMPTS.map((prompt, index) => (
            <div
              key={index}
              className={`absolute w-full px-6 transition-all duration-700 ease-in-out ${
                index === activeIndex
                  ? "opacity-100 transform-none"
                  : index < activeIndex || (activeIndex === 0 && index === PROMPTS.length - 1)
                  ? "opacity-0 -translate-y-4 pointer-events-none"
                  : "opacity-0 translate-y-4 pointer-events-none"
              }`}
            >
              <div className="font-mono text-base sm:text-lg text-white/90 leading-relaxed">
                <span className="text-action-blue mr-3">&gt;</span>
                {prompt}
              </div>
            </div>
          ))}
          
          <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-2">
            {PROMPTS.map((_, index) => (
              <button
                key={index}
                onClick={() => setActiveIndex(index)}
                className={`w-1.5 h-1.5 rounded-full transition-colors ${
                  index === activeIndex ? "bg-action-blue" : "bg-white/20 hover:bg-white/40"
                }`}
                aria-label={`Go to prompt ${index + 1}`}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
