import Link from "next/link";
import Image from "next/image";
import { LINKS } from "@/config/links";

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass-panel border-b border-b-white/10">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="relative w-8 h-8 rounded-lg overflow-hidden flex items-center justify-center bg-white/5 group-hover:bg-white/10 transition-colors border border-white/10">
              {/* Optional logo mark, fallback to text if not found */}
              <span className="font-oswald font-bold text-lg text-white">SQ</span>
            </div>
            <span className="font-oswald font-bold text-xl tracking-tight text-white">SportIQ</span>
          </Link>
        </div>

        <div className="hidden md:flex items-center gap-8">
          <Link href="#features" className="text-sm text-white/80 hover:text-white transition-colors">Features</Link>
          <Link href="#pricing" className="text-sm text-white/80 hover:text-white transition-colors">Pricing</Link>
          <Link href="#install" className="text-sm text-white/80 hover:text-white transition-colors">Install</Link>
          <a href={LINKS.github} target="_blank" rel="noopener noreferrer" className="text-sm text-white/80 hover:text-white transition-colors">GitHub</a>
        </div>

        <div className="flex items-center gap-4">
          <a
            href={LINKS.pypi}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white border border-white/20 rounded-lg hover:bg-white/10 transition-colors"
          >
            Install free
          </a>
          <Link
            href="#pricing"
            className="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-action-blue border border-action-blue rounded-full hover:bg-action-blue hover:text-white transition-colors"
          >
            Get Pro &rarr;
          </Link>
        </div>
      </div>
    </nav>
  );
}
