import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#38173E",
        "primary-container": "#502D55",
        secondary: "#935073",
        accent: "#F6DBC0",
        background: "#F8F4E9",
        surface: "#FFF7FA",
        "surface-container": "#F4ECF0",
        "surface-container-low": "#FAF1F5",
        "on-surface": "#1E1A1E",
        "on-surface-variant": "#4D444C",
        outline: "#7E747D",
        "outline-variant": "#D0C3CC"
      },
      fontFamily: {
        sans: ["var(--font-manrope)", "Manrope", "ui-sans-serif", "system-ui"]
      },
      spacing: {
        gutter: "24px",
        "glass-padding": "32px",
        "margin-desktop": "64px",
        "margin-mobile": "20px"
      },
      boxShadow: {
        glass: "0 28px 70px rgba(80, 45, 85, 0.08)",
        panel: "-16px 0 50px rgba(56, 23, 62, 0.10)"
      }
    }
  },
  plugins: []
};

export default config;
