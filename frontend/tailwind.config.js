/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Navy carries institutional trust. Green is the action colour —
        // go, approved, safe. Amber is reserved for anything time-critical.
        ink: "#0B2340",
        navy: { DEFAULT: "#12305A", deep: "#0B2340", soft: "#33507D" },
        grass: { DEFAULT: "#12724F", dark: "#0D5A3E", pale: "#E6F2EC" },
        paper: "#F2F5F7",
        rule: "#D9E0E6",
        urgent: "#B45309",
      },
      fontFamily: {
        display: ["Bitter", "Georgia", "serif"],
        sans: ["'Public Sans'", "system-ui", "sans-serif"],
      },
      maxWidth: { prose: "68ch" },
    },
  },
  plugins: [],
};
