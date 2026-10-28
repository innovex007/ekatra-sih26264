import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Ports differ from the Vite default because 5173/8000 are commonly taken by other local projects.
const UI_PORT = 5174;
const API_PORT = 8010;

export default defineConfig({
  plugins: [react()],
  server: {
    host: "localhost",
    port: UI_PORT,
    strictPort: true,
    proxy: { "/api": { target: `http://localhost:${API_PORT}`, rewrite: (p) => p.replace(/^\/api/, "") } },
  },
});
