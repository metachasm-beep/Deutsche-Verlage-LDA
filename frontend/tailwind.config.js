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
          900: "#1C1917",
          950: "#0C0A09",
        },
        gold: {
          DEFAULT: "#CA8A04",
          light: "#EAB308",
          dark: "#A16207",
        }
      },
      fontFamily: {
        heading: ["Crimson Pro", "serif"],
        body: ["Atkinson Hyperlegible", "sans-serif"],
      },
      animation: {
        "shiny-text": "shiny-text 2s infinite",
      },
      keyframes: {
        "shiny-text": {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.5 },
        },
      },
    },
  },
  plugins: [],
}
