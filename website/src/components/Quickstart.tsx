"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";

export default function Quickstart() {
  const [copied, setCopied] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const uvxCode = `uvx sportiq-mcp`;
  
  const claudeCode = `{
  "mcpServers": {
    "sportiq": {
      "command": "uvx",
      "args": ["sportiq-mcp"],
      "env": {
        "CRICAPI_KEY": "optional",
        "APIFOOTBALL_KEY": "optional",
        "THEODDS_KEY": "optional"
      }
    }
  }
}`;

  return (
    <section className="py-24">
      <div className="max-w-4xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="font-oswald text-3xl sm:text-4xl uppercase tracking-tight mb-4">
            Quickstart Config
          </h2>
        </div>

        <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl mb-8">
          <div className="flex items-center gap-2 px-6 py-4 border-b border-white/10 bg-black/20">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="ml-2 text-sm font-mono text-white/50">claude_desktop_config.json</span>
          </div>
          
          <div className="p-6 md:p-8 space-y-8">
            <div>
              <div className="flex justify-between items-center mb-3">
                <h4 className="text-sm font-medium text-white/80">Command Line</h4>
                <button 
                  onClick={() => copyToClipboard(uvxCode, 'uvx')}
                  className="text-white/50 hover:text-white transition-colors"
                  aria-label="Copy code"
                >
                  {copied === 'uvx' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <pre className="bg-black/40 p-4 rounded-xl overflow-x-auto text-sm font-mono text-white border border-white/5">
                <code>{uvxCode}</code>
              </pre>
            </div>

            <div>
              <div className="flex justify-between items-center mb-3">
                <h4 className="text-sm font-medium text-white/80">Claude Config (JSON)</h4>
                <button 
                  onClick={() => copyToClipboard(claudeCode, 'claude')}
                  className="text-white/50 hover:text-white transition-colors"
                  aria-label="Copy code"
                >
                  {copied === 'claude' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
              <pre className="bg-black/40 p-4 rounded-xl overflow-x-auto text-sm font-mono text-white border border-white/5">
                <code>{claudeCode}</code>
              </pre>
            </div>
          </div>
        </div>
        
        <div className="grid sm:grid-cols-2 gap-4 text-sm">
          <div className="glass-panel-light p-4 rounded-xl">
            <p className="text-white/90"><strong className="text-white">No keys?</strong> It still runs on free seed + public-source data.</p>
          </div>
          <div className="glass-panel-light p-4 rounded-xl">
            <p className="text-white/90"><strong className="text-white">No install?</strong> Add the hosted server as a custom connector — every tool, including the full intelligence layer, is <strong className="text-white">free</strong>: <code className="bg-white/10 text-white px-1 py-0.5 rounded text-xs font-mono">…run.app/mcp</code></p>
          </div>
        </div>
      </div>
    </section>
  );
}
