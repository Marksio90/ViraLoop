import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // NEXUS Brand Colors
        nexus: {
          50: "#f0f4ff",
          100: "#e0e9ff",
          200: "#c7d7fe",
          300: "#a5bcfd",
          400: "#8196f9",
          500: "#6366f1", // Primary
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        viral: {
          orange: "#f97316",
          red: "#ef4444",
          fire: "#ff4500",
        },
      },
      animation: {
        "gradient-x": "gradient-x 3s ease infinite",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "fade-in": "fade-in 0.5s ease-out",
        "slide-up": "slide-up 0.5s ease-out",
      },
      keyframes: {
        "gradient-x": {
          "0%, 100%": {
            "background-size": "200% 200%",
            "background-position": "left center",
          },
          "50%": {
            "background-size": "200% 200%",
            "background-position": "right center",
          },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { transform: "translateY(20px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
      backgroundImage: {
        "nexus-gradient":
          "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "viral-gradient":
          "linear-gradient(135deg, #f97316 0%, #ef4444 100%)",
        "dark-gradient":
          "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
