import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Qualyx Dashboard — Vite config (foundation only)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  }
});
