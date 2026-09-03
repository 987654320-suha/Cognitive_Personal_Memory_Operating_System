// 📁 LOCATION: frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}",
    "./src/app/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#f0f4ff",
          100: "#dde6ff",
          200: "#c0ceff",
          300: "#94a8ff",
          400: "#6377ff",
          500: "#3d4fff",
          600: "#2330f5",
          700: "#1a22e1",
          800: "#1c1fb6",
          900: "#1c1e8f",
          950: "#12135c",
        },
        surface: {
          DEFAULT: "#0f0f1a",
          card:    "#16162a",
          hover:   "#1e1e35",
          border:  "#2a2a45",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      animation: {
        "fade-in":     "fadeIn 0.3s ease-out",
        "slide-up":    "slideUp 0.4s ease-out",
        "pulse-glow":  "pulseGlow 2s ease-in-out infinite",
        "shimmer":     "shimmer 1.5s infinite",
      },
      keyframes: {
        fadeIn:    { "0%": { opacity: 0 },                        "100%": { opacity: 1 } },
        slideUp:   { "0%": { opacity: 0, transform: "translateY(16px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
        pulseGlow: { "0%,100%": { boxShadow: "0 0 20px rgba(99,119,255,0.3)" }, "50%": { boxShadow: "0 0 40px rgba(99,119,255,0.6)" } },
        shimmer:   { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
      },
      backdropBlur: { xs: "2px" },
    },
  },
  plugins: [],
};