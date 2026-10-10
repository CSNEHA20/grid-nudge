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
        background: "var(--background)",
        foreground: "var(--foreground)",
        navy: {
          950: "#090e17",
          900: "#0d1522",
          850: "#101a2a",
          800: "#131f32",
          750: "#18263d",
          700: "#1f304c",
          600: "#2a4165",
          500: "#3b5884",
        },
        nudge: {
          gold: "#facc15",
          yellow: "#fde047",
          amber: "#f59e0b",
          orange: "#f97316",
        },
        grid: {
          amber: "#f97316",
          orange: "#ea580c",
        },
        safety: {
          cyan: "#38bdf8",
          blue: "#0ea5e9",
          slate: "#64748b",
        },
      },
      boxShadow: {
        glow: "0 0 25px -5px rgba(250, 204, 21, 0.3)",
        "glow-orange": "0 0 25px -5px rgba(249, 115, 22, 0.35)",
        "glow-cyan": "0 0 25px -5px rgba(56, 189, 248, 0.3)",
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
      backgroundImage: {
        "striped-pattern": "repeating-linear-gradient(45deg, rgba(255,255,255,0.06), rgba(255,255,255,0.06) 8px, transparent 8px, transparent 16px)",
      },
    },
  },
  plugins: [],
};
export default config;
