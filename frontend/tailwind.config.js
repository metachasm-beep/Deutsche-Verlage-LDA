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
        }
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
