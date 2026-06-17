import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sky: {
          canvas: "#050505",
        },
        action: {
          blue: "#00f0ff",
        },
        midnight: {
          ink: "#000000",
        },
        cloud: {
          white: "#ffffff",
        },
        charcoal: {
          text: "#000000",
        },
        haze: {
          grey: "#f5f5f5",
        },
        sport: {
          football: "#16a34a",
          f1: "#e10600",
          cricket: "#f59e0b",
        },
      },
      fontFamily: {
        oswald: ["var(--font-oswald)", "sans-serif"],
        inter: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-space-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
