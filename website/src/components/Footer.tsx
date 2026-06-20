import Image from "next/image";
import Link from "next/link";
import { LINKS } from "@/config/links";

export default function Footer() {
  return (
    <footer className="py-12 border-t border-white/10 bg-black/40 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-16">
          <div className="col-span-2">
            <div className="flex items-center gap-2 mb-6">
              <Image
                src="/logo-full.png"
                alt="SportIQ"
                width={1476}
                height={488}
                className="h-9 w-auto"
              />
            </div>
            <p className="text-sm font-mono text-white/40 max-w-sm leading-relaxed">
              SportIQ is an analytics and entertainment tool. It surfaces probabilities and value — not guarantees. Bet responsibly, and only where it's legal for you.
            </p>
          </div>
          
          <div>
            <h4 className="font-inter font-medium text-white mb-4">Get Pro</h4>
            <ul className="space-y-3">
              <li><a href={LINKS.sponsors} target="_blank" rel="noopener noreferrer" className="text-sm text-white/60 hover:text-white transition-colors">GitHub Sponsors</a></li>
              <li><a href={LINKS.hostedMcp} target="_blank" rel="noopener noreferrer" className="text-sm text-white/60 hover:text-white transition-colors">Free hosted demo</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-inter font-medium text-white mb-4">Install</h4>
            <ul className="space-y-3">
              <li><Link href="/setup" className="text-sm text-white/60 hover:text-white transition-colors">Setup guide</Link></li>
              <li><a href={LINKS.pypi} className="text-sm text-white/60 hover:text-white transition-colors">PyPI</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-inter font-medium text-white mb-4">Source</h4>
            <ul className="space-y-3">
              <li><a href={LINKS.github} className="text-sm text-white/60 hover:text-white transition-colors">GitHub</a></li>
              <li><a href={LINKS.registry} className="text-sm text-white/60 hover:text-white transition-colors">MCP Registry</a></li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-inter font-medium text-white mb-4">Legal</h4>
            <ul className="space-y-3">
              <li><span className="text-sm text-white/60">MIT License</span></li>
              <li><a href={`mailto:${LINKS.email}`} className="text-sm text-white/60 hover:text-white transition-colors">Contact</a></li>
            </ul>
          </div>
        </div>
        
        <div className="border-t border-white/10 pt-8 flex flex-col md:flex-row items-center justify-between gap-4 text-xs font-mono text-white/40">
          <div>&copy; SportIQ 2026 &middot; MIT licensed</div>
          <div>Built by Utkarsh Gupta (@Ninjabeam20)</div>
        </div>
      </div>
    </footer>
  );
}
