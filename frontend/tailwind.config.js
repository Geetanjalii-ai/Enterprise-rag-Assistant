/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-muted": "var(--surface-muted)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        ink: "var(--ink)",
        "ink-hover": "var(--ink-hover)",
        text: "var(--text)",
        "text-muted": "var(--text-muted)",
        "text-subtle": "var(--text-subtle)",
        "focus-ring": "var(--focus-ring)",
        // Pastel mappings
        lavender: "var(--pastel-lavender-bg)",
        "lavender-text": "var(--pastel-lavender-text)",
        sky: "var(--pastel-sky-bg)",
        "sky-text": "var(--pastel-sky-text)",
        mint: "var(--pastel-mint-bg)",
        "mint-text": "var(--pastel-mint-text)",
        peach: "var(--pastel-peach-bg)",
        "peach-text": "var(--pastel-peach-text)",
        rose: "var(--pastel-rose-bg)",
        "rose-text": "var(--pastel-rose-text)",
        amber: "var(--pastel-amber-bg)",
        "amber-text": "var(--pastel-amber-text)",
      },
      fontFamily: {
        sans: ["'Inter Variable'", "sans-serif"],
      },
      borderRadius: {
        sm: "8px",
        md: "12px",
        lg: "16px",
      },
    },
  },
  plugins: [],
};
