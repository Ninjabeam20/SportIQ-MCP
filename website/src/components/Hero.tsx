"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export default function Hero() {
  const [typedText, setTypedText] = useState("");
  const fullText = "> Simulate the World Cup 2026 bracket 10,000×…";
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    let currentText = "";
    let currentIndex = 0;
    
    const typingInterval = setInterval(() => {
      if (currentIndex < fullText.length) {
        currentText += fullText[currentIndex];
        setTypedText(currentText);
        currentIndex++;
      } else {
        clearInterval(typingInterval);
        setTimeout(() => setShowResults(true), 400);
      }
    }, 40);

    return () => clearInterval(typingInterval);
  }, []);

  return (
    <section className="relative min-h-[90vh] flex items-center pt-24 pb-16 overflow-hidden">
      {/* Ambient BG elements */}
      <div className="absolute top-1/4 left-1/4 w-[40vw] h-[40vw] bg-sport-football/20 rounded-full blur-[120px] -z-10 mix-blend-screen opacity-50" />
      <div className="absolute bottom-1/4 right-1/4 w-[30vw] h-[30vw] bg-action-blue/20 rounded-full blur-[100px] -z-10 mix-blend-screen opacity-50" />

      <div className="max-w-7xl mx-auto px-4 w-full grid lg:grid-cols-2 gap-16 items-center">
        <div className="flex flex-col gap-8">
          <div className="space-y-6">
            <h1 className="font-oswald text-5xl sm:text-6xl lg:text-[5rem] leading-[0.9] font-bold text-white uppercase tracking-tight">
              Turn any AI into your personal sports analyst
            </h1>
            <p className="text-xl text-white/80 max-w-xl leading-relaxed">
              Monte Carlo World Cup sims, F1 pit strategy, Dream11 optimization & +EV value bets — inside your AI assistant.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <Link
              href="/setup"
              className="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-action-blue border border-action-blue rounded-full hover:bg-action-blue hover:text-white transition-colors"
            >
              Install free &rarr;
            </Link>
            <Link
              href="#pricing"
              className="inline-flex items-center justify-center px-6 py-3 text-base font-medium text-white border border-white/20 rounded-full hover:bg-white/10 transition-colors"
            >
              Sponsor the project
            </Link>
          </div>

          <div className="text-sm font-mono text-white/50 space-y-1">
            <p>Works with Claude · ChatGPT · Cursor · any MCP client</p>
            <p>· 44 tools · 3 sports</p>
          </div>
        </div>

        {/* Hero Console */}
        <div className="glass-panel rounded-2xl p-6 font-mono text-sm sm:text-base shadow-2xl relative">
          <div className="flex items-center gap-2 mb-4 pb-4 border-b border-white/10">
            <div className="w-3 h-3 rounded-full bg-red-500/50" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
            <div className="w-3 h-3 rounded-full bg-green-500/50" />
            <span className="ml-2 text-white/40 text-xs">sportiq-mcp</span>
          </div>

          <div className="space-y-4">
            <div className="text-white">
              {typedText}
              {!showResults && <span className="animate-pulse">_</span>}
            </div>

            {showResults && (
              <div className="space-y-3 pt-2 text-white/90 animate-in fade-in slide-in-from-bottom-2 duration-700">
                <div className="flex items-center justify-between group">
                  <span className="flex items-center gap-2 w-32"><span className="text-lg">🏆</span> Brazil</span>
                  <span className="text-sport-football font-bold w-12 text-right">18.4%</span>
                  <div className="flex-1 h-1.5 bg-white/10 rounded-full ml-4 overflow-hidden">
                    <div className="h-full bg-sport-football w-[18.4%] rounded-full shadow-[0_0_10px_rgba(22,163,74,0.5)]" />
                  </div>
                </div>
                
                <div className="flex items-center justify-between group">
                  <span className="flex items-center gap-2 w-32"><span className="text-lg">🇫🇷</span> France</span>
                  <span className="text-white/80 w-12 text-right">15.1%</span>
                  <div className="flex-1 h-1.5 bg-white/10 rounded-full ml-4 overflow-hidden">
                    <div className="h-full bg-white/40 w-[15.1%] rounded-full" />
                  </div>
                </div>
                
                <div className="flex items-center justify-between group">
                  <span className="flex items-center gap-2 w-32"><span className="text-lg">🇦🇷</span> Argentina</span>
                  <span className="text-white/80 w-12 text-right">12.7%</span>
                  <div className="flex-1 h-1.5 bg-white/10 rounded-full ml-4 overflow-hidden">
                    <div className="h-full bg-white/30 w-[12.7%] rounded-full" />
                  </div>
                </div>
                
                <div className="flex items-center justify-between group">
                  <span className="flex items-center gap-2 w-32"><span className="text-lg">🏴󠁧󠁢󠁥󠁮󠁧󠁿</span> England</span>
                  <span className="text-white/80 w-12 text-right">9.8%</span>
                  <div className="flex-1 h-1.5 bg-white/10 rounded-full ml-4 overflow-hidden">
                    <div className="h-full bg-white/20 w-[9.8%] rounded-full" />
                  </div>
                </div>
                
                <div className="mt-4 pt-4 border-t border-white/5 text-xs text-white/40 flex justify-between">
                  <span>*Illustrative simulation data</span>
                  <span>10,000 iterations</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
