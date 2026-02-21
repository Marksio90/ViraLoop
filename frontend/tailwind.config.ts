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
        viraloop: {
          purple:  "#7c3aed",
          cyan:    "#06b6d4",
          amber:   "#f59e0b",
          bg:      "#050510",
          surface: "#0d0d1f",
        },
      },
      fontFamily: {
        sans:    ["Inter", "system-ui", "sans-serif"],
        grotesk: ["Space Grotesk", "system-ui", "sans-serif"],
        bebas:   ["Bebas Neue", "sans-serif"],
      },
      animation: {
        "fade-in":     "fadeIn 0.5s ease both",
        "slide-in":    "slideInLeft 0.4s ease both",
        "pulse-glow":  "pulse-glow 3s ease-in-out infinite",
        "float":       "float 4s ease-in-out infinite",
        "spin-slow":   "spin-slow 12s linear infinite",
        "shimmer":     "shimmer 2s infinite",
        "wave":        "wave 1s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        slideInLeft: {
          from: { opacity: "0", transform: "translateX(-20px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 20px rgba(124,58,237,0.2)" },
          "50%":      { boxShadow: "0 0 40px rgba(124,58,237,0.5), 0 0 80px rgba(124,58,237,0.15)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%":      { transform: "translateY(-8px)" },
        },
        "spin-slow": {
          from: { transform: "rotate(0deg)" },
          to:   { transform: "rotate(360deg)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% center" },
          "100%": { backgroundPosition: "200% center" },
        },
        wave: {
          "0%, 100%": { transform: "scaleY(0.5)" },
          "50%":      { transform: "scaleY(1.5)" },
        },
      },
      backgroundImage: {
        "viraloop-gradient": "linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%)",
        "dark-grid":
          "linear-gradient(rgba(124,58,237,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,0.04) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};

export default config;
