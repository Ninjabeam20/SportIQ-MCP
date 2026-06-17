"use client";

import { useEffect, useState, useRef } from "react";

export default function TrustStrip() {
  const [toolsCount, setToolsCount] = useState(0);
  const sectionRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          let start = 0;
          const target = 44;
          const duration = 1500;
          const increment = target / (duration / 16);
          
          const timer = setInterval(() => {
            start += increment;
            if (start >= target) {
              setToolsCount(target);
              clearInterval(timer);
            } else {
              setToolsCount(Math.floor(start));
            }
          }, 16);
          
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    
    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }
    
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={sectionRef} className="py-12 border-y border-white/5 bg-white/5">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex flex-col md:flex-row items-center justify-between gap-8 text-sm font-inter text-white/60">
          <div className="flex items-center gap-6 flex-wrap justify-center">
            <span className="font-medium text-white/80">Works with</span>
            <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10">Claude</span>
            <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10">ChatGPT</span>
            <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10">Cursor</span>
            <span>any MCP client</span>
          </div>
          
          <div className="flex items-center gap-6 flex-wrap justify-center">
            <span className="flex items-center gap-2">
              <svg className="w-5 h-5 opacity-70" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
              PyPI
            </span>
            <span className="flex items-center gap-2">
              <svg className="w-5 h-5 opacity-70" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
              MCP Registry
            </span>
            <span className="flex items-center gap-2">
              <svg className="w-5 h-5 opacity-70" viewBox="0 0 24 24" fill="currentColor"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/></svg>
              MIT Licensed
            </span>
            <span className="text-white font-mono font-bold text-base flex items-center gap-2 bg-white/10 px-4 py-1.5 rounded-full border border-white/20">
              <span className="text-action-blue">{toolsCount}</span> tools
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
