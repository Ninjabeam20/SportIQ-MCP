import type { Metadata, Viewport } from "next";
import { Inter, Oswald, Space_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["500"],
  variable: "--font-inter",
});

const oswald = Oswald({
  subsets: ["latin"],
  weight: ["700"],
  variable: "--font-oswald",
});

const spaceMono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-space-mono",
});

export const viewport: Viewport = {
  themeColor: "#050505",
};

export const metadata: Metadata = {
  title: "SportIQ — AI sports intelligence for football, F1 & cricket",
  description: "SportIQ plugs 46 sports tools into any AI (Claude, ChatGPT, Cursor): FIFA World Cup 2026 football, Formula 1, and IPL cricket. Ask in plain English — it replays the World Cup 2026 and runs what-ifs, simulates the F1 title race, models pit strategy, builds Dream11 teams, and surfaces model-vs-market edges (positive-EV filtered). Free, open-source, installs in seconds via uvx.",
  metadataBase: new URL("https://sport-iq-sports-analysis.vercel.app"),
  openGraph: {
    title: "SportIQ — AI sports intelligence for football, F1 & cricket",
    description: "An MCP server that gives Claude — and any AI assistant — World Cup 2026 replays and what-ifs, an F1 title-race simulator, pit-strategy prediction, and Dream11 optimization.",
    url: "https://sport-iq-sports-analysis.vercel.app",
    siteName: "SportIQ",
    images: [
      {
        url: "/logo-full.png",
        width: 1476,
        height: 488,
        alt: "SportIQ — AI sports intelligence for football, F1 & cricket",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "SportIQ — AI sports intelligence for football, F1 & cricket",
    description: "An MCP server that gives Claude — and any AI assistant — World Cup 2026 replays and what-ifs, an F1 title-race simulator, pit-strategy prediction, and Dream11 optimization.",
    images: ["/logo-full.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "SportIQ",
              applicationCategory: "SportsApplication",
              operatingSystem: "Any",
            }),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "FAQPage",
              mainEntity: [
                {
                  "@type": "Question",
                  name: "What is an MCP server?",
                  acceptedAnswer: {
                    "@type": "Answer",
                    text: "An MCP (Model Context Protocol) server allows AI assistants to use external tools and data.",
                  },
                },
                {
                  "@type": "Question",
                  name: "Which AIs work?",
                  acceptedAnswer: {
                    "@type": "Answer",
                    text: "It works with Claude Desktop, Claude Code, ChatGPT, Cursor, and any MCP client.",
                  },
                },
                {
                  "@type": "Question",
                  name: "Is it free?",
                  acceptedAnswer: {
                    "@type": "Answer",
                    text: "Yes — all 46 tools are free, including the full intelligence layer: World Cup replays and what-ifs, the F1 title-race simulator, pit-strategy models, Dream11 optimizers, and model-vs-market edges. The hosted server needs no key; some live feeds need provider keys when self-hosting.",
                  },
                },
                {
                  "@type": "Question",
                  name: "How can I support SportIQ?",
                  acceptedAnswer: {
                    "@type": "Answer",
                    text: "Every tool is free, but you can sponsor SportIQ on GitHub — Supporter ($5/mo), Backer ($10/mo), or Lifetime ($49 one-time) — to help cover hosting and keep the project maintained. Purely voluntary; you get the same fully-unlocked server either way.",
                  },
                },
                {
                  "@type": "Question",
                  name: "Is betting advice guaranteed?",
                  acceptedAnswer: {
                    "@type": "Answer",
                    text: "No. SportIQ is an analytics and entertainment tool. It surfaces probabilities and value — not guarantees.",
                  },
                },
              ],
            }),
          }}
        />
      </head>
      <body className={`${inter.variable} ${oswald.variable} ${spaceMono.variable} font-inter bg-sky-canvas text-cloud-white antialiased`}>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
