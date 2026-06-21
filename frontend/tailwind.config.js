/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Kairos design spec — exact values from the project context doc
        bg: "#0B120E",
        surface: "#131A15",
        raised: "#1A231C",
        line: "#243027",
        amber: "#E8A318",
        teal: "#00BFA8",
        ink: "#E8EFE9",
        dim: "#8A9E8C",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        panel: "0 8px 32px rgba(0,0,0,0.55)",
        glow: "0 0 24px rgba(0,191,168,0.25)",
      },
    },
  },
  plugins: [],
};
