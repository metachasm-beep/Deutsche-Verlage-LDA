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
          800: "#14161D",
          900: "#0D0E12",
          950: "#070709",
        },
        gold: {
          DEFAULT: "#D4AF37",
          light: "#FACC15",
          dark: "#A16207",
        },
        archetype: {
          traditional: "#EAB308",
          neoliberal: "#38BDF8",
          critical: "#FB7185",
        }
      },
      fontFamily: {
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
