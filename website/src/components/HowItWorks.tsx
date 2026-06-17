import Image from "next/image";

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
            <h3 className="font-oswald text-xl uppercase tracking-tight mb-3">Buy Pro</h3>
            <p className="text-sm text-white/60">checkout on Polar &rarr;</p>
            <p className="text-sm text-white/60 mt-2">get your sq_ key by email</p>
          </div>

          {/* Step 3 */}
          <div className="text-center">
            <div className="w-12 h-12 rounded-full bg-action-blue/20 flex items-center justify-center font-oswald text-2xl mx-auto mb-6 text-action-blue border border-action-blue/30">3</div>
            <h3 className="font-oswald text-xl uppercase tracking-tight mb-3">Unlock</h3>
            <p className="text-sm font-mono text-white/60">set SPORTIQ_PRO_KEY</p>
            <p className="text-sm text-white/60 mt-2">in your config. Done.</p>
          </div>
        </div>

        {/* Screenshot Strip */}
        <div className="relative max-w-6xl mx-auto">
          <div className="absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-[#3c597d] to-transparent z-10" />
          <div className="absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-[#3c597d] to-transparent z-10" />
          
          <div className="flex gap-4 overflow-x-auto hide-scrollbar snap-x pb-8 pt-4 px-8">
            {[1, 2, 3, 4].map((step) => (
              <div key={step} className="flex-none w-[80vw] sm:w-[600px] snap-center">
                <div className="relative aspect-[3/2] w-full rounded-xl overflow-hidden glass-panel border-white/20 shadow-2xl">
                  {/* Fallback box if image missing */}
                  <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                    <span className="font-mono text-white/30 text-sm">step-{step}.png</span>
                  </div>
                  {/* <Image 
                    src={`/step-${step}.png`} 
                    alt={`Connection step ${step}`}
                    fill
                    className="object-cover"
                    sizes="(max-width: 768px) 80vw, 600px"
                  /> */}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
