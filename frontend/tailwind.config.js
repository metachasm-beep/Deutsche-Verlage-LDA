/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        midnight: {
          800: "rgb(var(--c-obsidian-800) / <alpha-value>)",
          900: "rgb(var(--c-obsidian-900) / <alpha-value>)",
          950: "rgb(var(--c-obsidian-950) / <alpha-value>)",
        },
        obsidian: {
          700: "rgb(var(--c-obsidian-700) / <alpha-value>)",
          800: "rgb(var(--c-obsidian-800) / <alpha-value>)",
          850: "rgb(var(--c-obsidian-850) / <alpha-value>)",
          900: "rgb(var(--c-obsidian-900) / <alpha-value>)",
          950: "rgb(var(--c-obsidian-950) / <alpha-value>)",
        },
        parchment: {
          50: "rgb(var(--c-parchment-50) / <alpha-value>)",
          100: "rgb(var(--c-parchment-100) / <alpha-value>)",
          200: "rgb(var(--c-parchment-200) / <alpha-value>)",
          300: "rgb(var(--c-parchment-300) / <alpha-value>)",
          400: "rgb(var(--c-parchment-400) / <alpha-value>)",
        },
        gold: {
          DEFAULT: "rgb(var(--c-traditional) / <alpha-value>)",
          light: "rgb(var(--c-traditional-light) / <alpha-value>)",
          dark: "rgb(var(--c-traditional-dark) / <alpha-value>)",
        },
        traditional: {
          DEFAULT: "rgb(var(--c-traditional) / <alpha-value>)",
          light: "rgb(var(--c-traditional-light) / <alpha-value>)",
          dark: "rgb(var(--c-traditional-dark) / <alpha-value>)",
          subtle: "var(--c-traditional-subtle)",
        },
        neoliberal: {
          DEFAULT: "rgb(var(--c-neoliberal) / <alpha-value>)",
          light: "rgb(var(--c-neoliberal-light) / <alpha-value>)",
          dark: "rgb(var(--c-neoliberal-dark) / <alpha-value>)",
          subtle: "var(--c-neoliberal-subtle)",
        },
        critical: {
          DEFAULT: "rgb(var(--c-critical) / <alpha-value>)",
          light: "rgb(var(--c-critical-light) / <alpha-value>)",
          dark: "rgb(var(--c-critical-dark) / <alpha-value>)",
          subtle: "var(--c-critical-subtle)",
        },
        hybrid: {
          DEFAULT: "rgb(var(--c-hybrid) / <alpha-value>)",
          light: "rgb(var(--c-hybrid-light) / <alpha-value>)",
          dark: "rgb(var(--c-hybrid-dark) / <alpha-value>)",
          subtle: "var(--c-hybrid-subtle)",
        },
        archetype: {
          traditional: "rgb(var(--c-traditional) / <alpha-value>)",
          neoliberal: "rgb(var(--c-neoliberal) / <alpha-value>)",
          critical: "rgb(var(--c-critical) / <alpha-value>)",
        },
        // Harmonized Editorial Pigments (replacing raw neon Tailwind accents)
        emerald: {
          200: "#C5DDD4",
          300: "#8AB8A8",
          400: "#689F8D",
          500: "#4D8573",
          950: "#11221D",
        },
        amber: {
          200: "#E8D3B3",
          300: "#D6B27C",
          400: "#C99A5B",
          500: "#B08040",
          950: "#241A0D",
        },
        sky: {
          200: "#BFDCE0",
          300: "#86BAC2",
          400: "#5B9EA6",
          500: "#43838B",
          950: "#0F2024",
        },
        rose: {
          200: "#E6C2BF",
          300: "#D8948E",
          400: "#C6716B",
          500: "#AD5650",
          950: "#261211",
        },
        purple: {
          200: "#D6CEE8",
          300: "#B2A5D1",
          400: "#9283B8",
          500: "#76669E",
          950: "#1B1626",
        },
        violet: {
          200: "#D6CEE8",
          300: "#B2A5D1",
          400: "#9283B8",
          500: "#76669E",
          950: "#1B1626",
        },
      },
      fontFamily: {
        serif: ["Cormorant Garamond", "Georgia", "serif"],
        sans: ["Plus Jakarta Sans", "system-ui", "sans-serif"],
        heading: ["Cormorant Garamond", "Georgia", "serif"],
        body: ["Plus Jakarta Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      animation: {
        "shiny-text": "shiny-text 3s infinite",
      },
      keyframes: {
        "shiny-text": {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.65 },
        },
      },
    },
  },
  plugins: [],
}
