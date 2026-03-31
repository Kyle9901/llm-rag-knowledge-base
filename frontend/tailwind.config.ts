import type { Config } from "tailwindcss";

// Keep content globs explicit to avoid missing class extraction.
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
} satisfies Config;
