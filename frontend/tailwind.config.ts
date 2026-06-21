import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Material Design 3 color tokens (baseline purple scheme)
        md: {
          primary:            "#6750A4",
          "on-primary":       "#FFFFFF",
          "primary-container":"#EADDFF",
          "on-primary-container": "#21005D",
          secondary:          "#625B71",
          "on-secondary":     "#FFFFFF",
          "secondary-container": "#E8DEF8",
          "on-secondary-container": "#1D192B",
          tertiary:           "#7D5260",
          "on-tertiary":      "#FFFFFF",
          "tertiary-container": "#FFD8E4",
          error:              "#B3261E",
          "error-container":  "#F9DEDC",
          "on-error":         "#FFFFFF",
          "on-error-container": "#410E0B",
          background:         "#FFFBFE",
          "on-background":    "#1C1B1F",
          surface:            "#FFFBFE",
          "on-surface":       "#1C1B1F",
          "surface-variant":  "#E7E0EC",
          "on-surface-variant": "#49454F",
          outline:            "#79747E",
          "outline-variant":  "#CAC4D0",
          "inverse-surface":  "#313033",
          "inverse-on-surface": "#F4EFF4",
          // Elevation surfaces (tinted with primary)
          "surface-1":        "#F4EEFF",
          "surface-2":        "#EFE8FB",
          "surface-3":        "#E9E0F8",
        },
      },
      fontFamily: {
        sans: ["Roboto", "system-ui", "sans-serif"],
      },
      boxShadow: {
        // MD3 elevation levels
        "md-1": "0px 1px 2px rgba(0,0,0,0.3), 0px 1px 3px 1px rgba(0,0,0,0.15)",
        "md-2": "0px 1px 2px rgba(0,0,0,0.3), 0px 2px 6px 2px rgba(0,0,0,0.15)",
        "md-3": "0px 1px 3px rgba(0,0,0,0.3), 0px 4px 8px 3px rgba(0,0,0,0.15)",
        "md-4": "0px 2px 3px rgba(0,0,0,0.3), 0px 6px 10px 4px rgba(0,0,0,0.15)",
      },
      borderRadius: {
        "md-xs": "4px",
        "md-sm": "8px",
        "md-md": "12px",
        "md-lg": "16px",
        "md-xl": "28px",
        "md-full": "50px",
      },
      keyframes: {
        "md-bounce": {
          "0%, 60%, 100%": { transform: "translateY(0)" },
          "30%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "md-bounce-1": "md-bounce 1.2s ease-in-out infinite 0ms",
        "md-bounce-2": "md-bounce 1.2s ease-in-out infinite 200ms",
        "md-bounce-3": "md-bounce 1.2s ease-in-out infinite 400ms",
      },
    },
  },
  plugins: [],
};

export default config;
