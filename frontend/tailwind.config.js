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
        obsidian: {
          700: "#1F222E",
          800: "#14161D",
          850: "#101218",
          900: "#0D0E12",
          950: "#070709",
        },
        parchment: {
          50: "#FDFBF7",
          100: "#F6F1E6",
          200: "#E2DAC8",
          300: "#A8A090",
          400: "#787062",
        },
        gold: {
          DEFAULT: "#D4AF37",
          light: "#FACC15",
          dark: "#A16207",
        },
        traditional: {
          DEFAULT: "#D4AF37",
          light: "#FACC15",
          dark: "#A16207",
          subtle: "rgba(212, 175, 55, 0.14)",
        },
        neoliberal: {
          DEFAULT: "#38BDF8",
          light: "#7DD3FC",
          dark: "#0284C7",
          subtle: "rgba(56, 189, 248, 0.14)",
        },
        critical: {
          DEFAULT: "#FB7185",
          light: "#FDA4AF",
          dark: "#E11D48",
          subtle: "rgba(251, 113, 133, 0.14)",
        },
        hybrid: {
          DEFAULT: "#A78BFA",
          light: "#C4B5FD",
          dark: "#7C3AED",
          subtle: "rgba(167, 139, 250, 0.14)",
        },
        archetype: {
          traditional: "#EAB308",
          neoliberal: "#38BDF8",
          critical: "#FB7185",
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
