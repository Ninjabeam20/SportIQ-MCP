export const LINKS = {
  // Buy / support — pricing lives on GitHub Sponsors
  sponsors: "https://github.com/sponsors/Ninjabeam20",
  // Install
  pypi: "https://pypi.org/project/sportiq-mcp/",
  // Free hosted demo server (custom connector) — every tool free right now
  hostedMcp: "https://sportiq-mcp-329580761892.us-central1.run.app/mcp",
  // Source
  github: "https://github.com/Ninjabeam20/SportIQ-MCP",
  registry: "https://registry.modelcontextprotocol.io",
  registryId: "io.github.Ninjabeam20/sportiq-mcp",
  email: "utkarshgupta885@gmail.com",
} as const;

export type Plan = "supporter" | "pro" | "lifetime";

export type Tier = {
  plan: Plan;
  name: string;
  price: string;
  cadence: string;
  tagline: string;
  featured?: boolean;
  badge?: string;
};

// Single source of truth for sponsorship tiers. All tiers check out on GitHub
// Sponsors. Every tool is free for everyone — sponsoring is purely voluntary
// support, not an unlock.
export const PRICING: Tier[] = [
  {
    plan: "supporter",
    name: "Supporter",
    price: "$5",
    cadence: "/mo",
    tagline: "Chip in monthly to help cover hosting and data costs.",
  },
  {
    plan: "pro",
    name: "Pro",
    price: "$10",
    cadence: "/mo",
    tagline: "Back the project seriously and keep all 44 tools maintained.",
    featured: true,
    badge: "★ Most popular",
  },
  {
    plan: "lifetime",
    name: "Lifetime",
    price: "$49",
    cadence: "once",
    tagline: "One-time thank-you that funds the servers for good.",
  },
];
