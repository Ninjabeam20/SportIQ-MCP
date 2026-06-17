export const LINKS = {
  pypi: "https://pypi.org/project/sportiq-mcp/",
  github: "https://github.com/Ninjabeam20/SportIQ-MCP",
  registry: "https://registry.modelcontextprotocol.io", // id: io.github.Ninjabeam20/sportiq-mcp
  hostedMcp: "https://sportiq-mcp-329580761892.us-central1.run.app/mcp",
  email: "utkarshgupta885@gmail.com",
} as const;

export type Provider = "polar" | "lemonsqueezy" | "paddle" | "gumroad" | "stripe";
export type Plan = "monthly" | "annual" | "lifetime";

// null = not wired yet → render button as "Coming soon" + disabled.
export const CHECKOUT: Record<Provider, Record<Plan, string | null>> = {
  polar: {
    monthly: "https://polar.sh/CHANGE-ME/sportiq-pro?plan=monthly",
    annual: "https://polar.sh/CHANGE-ME/sportiq-pro?plan=annual",
    lifetime: "https://polar.sh/CHANGE-ME/sportiq-pro?plan=lifetime",
  },
  lemonsqueezy: { monthly: null, annual: null, lifetime: null },
  paddle: { monthly: null, annual: null, lifetime: null },
  gumroad: { monthly: null, annual: null, lifetime: null },
  stripe: { monthly: null, annual: null, lifetime: null },
};

export const DEFAULT_PROVIDER: Provider = "polar";
