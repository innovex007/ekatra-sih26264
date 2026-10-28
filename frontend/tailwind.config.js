/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#14325C", amber: { ekatra: "#F5A623" }, canvas: "#F7F8FA", line: "#E5E7EB",
        sev: {
          conflict: "#C62828", conflictBg: "#FDE3E3", duplicate: "#C25E00", duplicateBg: "#FFEEDD",
          related: "#8A6D00", relatedBg: "#FFF6CC", info: "#555555", infoBg: "#EEEEEE",
        },
        bureau: { pgrc: "#2F6FDE", rb: "#7B3FC4", approval: "#0F9488", academic: "#3C9A3C", regional: "#5B6B7F" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "Segoe UI", "sans-serif"] },
      boxShadow: { card: "0 1px 2px rgba(16,24,40,.05), 0 1px 3px rgba(16,24,40,.06)" },
    },
  },
  plugins: [],
};
