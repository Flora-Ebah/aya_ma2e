import type { Config } from "tailwindcss";

/**
 * Config Tailwind MA2E — mappée sur les tokens design GS2E
 * (voir public/design/tokens.css importé dans globals.css).
 * Les couleurs sont écrites `rgb(var(--color-x) / <alpha-value>)` pour
 * supporter les opacités Tailwind et basculer light/dark via [data-theme].
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-outfit)", "system-ui", "sans-serif"],
        display: ["var(--font-sora)", "var(--font-outfit)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "ui-monospace", "monospace"],
        sidebar: ["var(--font-outfit)", "system-ui", "sans-serif"],
      },
      colors: {
        // === Brand GS2E (bleu SARA Light) ===
        primary: {
          DEFAULT: "rgb(var(--color-brand-primary) / <alpha-value>)",
          soft: "rgb(var(--color-brand-primary-soft) / <alpha-value>)",
          subtle: "rgb(var(--color-brand-primary-subtle) / <alpha-value>)",
          hover: "rgb(var(--color-brand-primary-hover) / <alpha-value>)",
          active: "rgb(var(--color-brand-primary-active) / <alpha-value>)",
          contrast: "rgb(var(--color-brand-primary-contrast) / <alpha-value>)",
          50:  "rgb(var(--color-brand-primary-subtle) / <alpha-value>)",
          100: "rgb(var(--color-brand-primary-soft) / <alpha-value>)",
          500: "rgb(var(--color-brand-primary) / <alpha-value>)",
          600: "rgb(var(--color-brand-primary) / <alpha-value>)",
          700: "rgb(var(--color-brand-primary-hover) / <alpha-value>)",
          800: "rgb(var(--color-brand-primary-active) / <alpha-value>)",
        },
        // === Accent (vert MA2E) ===
        accent: {
          DEFAULT: "rgb(var(--color-brand-accent) / <alpha-value>)",
          soft: "rgb(var(--color-brand-accent-soft) / <alpha-value>)",
          hover: "rgb(var(--color-brand-accent-hover) / <alpha-value>)",
          strong: "rgb(var(--color-brand-accent-strong) / <alpha-value>)",
          text: "rgb(var(--color-brand-accent-text) / <alpha-value>)",
          500: "rgb(var(--color-brand-accent) / <alpha-value>)",
          600: "rgb(var(--color-brand-accent-hover) / <alpha-value>)",
        },
        // === Surfaces ===
        canvas: "rgb(var(--color-bg-canvas) / <alpha-value>)",
        surface: {
          DEFAULT: "rgb(var(--color-bg-surface) / <alpha-value>)",
          elevated: "rgb(var(--color-bg-surface-elevated) / <alpha-value>)",
          subtle: "rgb(var(--color-bg-surface-subtle) / <alpha-value>)",
          hover: "rgb(var(--color-bg-surface-hover) / <alpha-value>)",
          inverse: "rgb(var(--color-bg-inverse) / <alpha-value>)",
        },
        // === Textes ===
        ink: {
          DEFAULT: "rgb(var(--color-text-primary) / <alpha-value>)",
          primary: "rgb(var(--color-text-primary) / <alpha-value>)",
          secondary: "rgb(var(--color-text-secondary) / <alpha-value>)",
          muted: "rgb(var(--color-text-muted) / <alpha-value>)",
          disabled: "rgb(var(--color-text-disabled) / <alpha-value>)",
          inverse: "rgb(var(--color-text-inverse) / <alpha-value>)",
          // Nuances compat Tailwind (toutes mappées sur les tokens texte)
          50:  "rgb(var(--color-bg-surface-subtle) / <alpha-value>)",
          100: "rgb(var(--color-bg-surface-hover) / <alpha-value>)",
          200: "rgb(var(--color-border-default) / <alpha-value>)",
          300: "rgb(var(--color-border-strong) / <alpha-value>)",
          400: "rgb(var(--color-text-muted) / <alpha-value>)",
          500: "rgb(var(--color-text-secondary) / <alpha-value>)",
          600: "rgb(var(--color-text-secondary) / <alpha-value>)",
          700: "rgb(var(--color-text-primary) / <alpha-value>)",
          800: "rgb(var(--color-text-primary) / <alpha-value>)",
          900: "rgb(var(--color-text-primary) / <alpha-value>)",
          950: "rgb(var(--color-bg-inverse) / <alpha-value>)",
        },
        // === Bordures ===
        border: {
          DEFAULT: "rgb(var(--color-border-default) / <alpha-value>)",
          subtle: "rgb(var(--color-border-subtle) / <alpha-value>)",
          strong: "rgb(var(--color-border-strong) / <alpha-value>)",
          input: "rgb(var(--color-border-input) / <alpha-value>)",
          focus: "rgb(var(--color-border-focus) / <alpha-value>)",
        },
        // === Statuts ===
        success: {
          DEFAULT: "rgb(var(--color-status-success) / <alpha-value>)",
          soft: "rgb(var(--color-status-success-soft) / <alpha-value>)",
        },
        warning: {
          DEFAULT: "rgb(var(--color-status-warning) / <alpha-value>)",
          soft: "rgb(var(--color-status-warning-soft) / <alpha-value>)",
        },
        danger: {
          DEFAULT: "rgb(var(--color-status-error) / <alpha-value>)",
          soft: "rgb(var(--color-status-error-soft) / <alpha-value>)",
          strong: "rgb(var(--color-status-error-strong) / <alpha-value>)",
        },
        info: {
          DEFAULT: "rgb(var(--color-status-info) / <alpha-value>)",
          soft: "rgb(var(--color-status-info-soft) / <alpha-value>)",
        },
      },
      boxShadow: {
        soft: "0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.06)",
        card: "0 1px 3px 0 rgb(15 23 42 / 0.05), 0 4px 12px -2px rgb(15 23 42 / 0.06)",
        floating: "0 10px 25px -5px rgb(15 23 42 / 0.10), 0 8px 10px -6px rgb(15 23 42 / 0.05)",
      },
      borderRadius: {
        none: "0",
        sm: "4px",
        DEFAULT: "6px",
        md: "6px",
        lg: "8px",
        xl: "12px",
        "2xl": "16px",
        "3xl": "20px",
        full: "9999px",
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.25s ease-out",
      },
      keyframes: {
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
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
