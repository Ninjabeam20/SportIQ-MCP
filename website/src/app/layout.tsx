import type { Metadata, Viewport } from "next";
import { Inter, Oswald, Space_Mono } from "next/font/google";
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
  description: "SportIQ plugs 44 live sports tools into any AI (Claude, ChatGPT, Cursor): FIFA World Cup 2026 football, Formula 1, and IPL cricket. Ask in plain English — it simulates brackets, finds value bets, optimizes Dream11 teams, and models F1 pit strategy. Free, open-source, installs in seconds via uvx.",
  metadataBase: new URL("https://sportiq.app"),
  openGraph: {
    title: "SportIQ — AI sports intelligence for football, F1 & cricket",
    description: "An MCP server that gives Claude — and any AI assistant — Monte Carlo World Cup simulations, F1 pit-strategy prediction, and Dream11 optimization.",
    url: "https://sportiq.app",
    siteName: "SportIQ",
    images: [
      {
        url: "/og.png",
        width: 1200,
        height: 630,
        alt: "SportIQ — AI sports intelligence for football, F1 & cricket",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "SportIQ — AI sports intelligence for football, F1 & cricket",
    description: "An MCP server that gives Claude — and any AI assistant — Monte Carlo World Cup simulations, F1 pit-strategy prediction, and Dream11 optimization.",
    images: ["/og.png"],
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
              offers: [
                {
                  "@type": "Offer",
                  price: "0",
                  priceCurrency: "USD",
                },
                {
                  "@type": "Offer",
                  price: "5",
                  priceCurrency: "USD",
                },
                {
                  "@type": "Offer",
                  price: "10",
                  priceCurrency: "USD",
                },
                {
                  "@type": "Offer",
                  price: "49",
                  priceCurrency: "USD",
                },
              ],
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
                    text: "Yes, the free layer gives you live scores, fixtures, standings, and basic stats. The Pro layer unlocks intelligent modeling like Monte Carlo bracket simulations and Dream11 optimizers.",
                  },
                },
                {
                  "@type": "Question",
                  name: "How do I unlock Pro?",
                  acceptedAnswer: {
                    "@type": "Answer",
                    text: "Sponsor SportIQ on GitHub at the Pro ($10/mo) or Lifetime ($49 one-time) tier. Your Pro key arrives instantly in the sponsorship welcome message — paste it into your MCP config as SPORTIQ_PRO_KEY to unlock all 24 intelligence tools.",
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
      </body>
    </html>
  );
}
