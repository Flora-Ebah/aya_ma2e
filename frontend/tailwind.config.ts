import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-inter)", "system-ui", "sans-serif"],
        sidebar: ["var(--font-sidebar)", "system-ui", "sans-serif"],
      },
      colors: {
        ink: {
          50: "#F8FAFC",
          100: "#F1F5F9",
          200: "#E2E8F0",
          300: "#CBD5E1",
          400: "#94A3B8",
          500: "#64748B",
          600: "#475569",
          700: "#334155",
          800: "#1E293B",
          900: "#0F172A",
          950: "#020617",
        },
        primary: {
          50: "#E6F7EE",
          100: "#C2ECD3",
          200: "#8BD8AB",
          300: "#54C383",
          400: "#2DB46A",
          500: "#00A045",
          600: "#00913D",
          700: "#007D34",
          800: "#00682B",
          900: "#004D1F",
        },
        accent: {
          50: "#FFF6E5",
          100: "#FFE7B8",
          200: "#FFD485",
          300: "#FFC152",
          400: "#FFB429",
          500: "#FFA500",
          600: "#E69400",
          700: "#CC7F00",
          800: "#A36600",
          900: "#7A4D00",
        },
      },
      boxShadow: {
        soft: "0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.06)",
        card: "0 1px 3px 0 rgb(15 23 42 / 0.05), 0 4px 12px -2px rgb(15 23 42 / 0.06)",
        floating: "0 10px 25px -5px rgb(15 23 42 / 0.10), 0 8px 10px -6px rgb(15 23 42 / 0.05)",
      },
      borderRadius: {
        none: "0",
        sm: "2px",
        DEFAULT: "3px",
        md: "3px",
        lg: "4px",
        xl: "4px",
        "2xl": "4px",
        "3xl": "6px",
        full: "9999px",
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.25s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
