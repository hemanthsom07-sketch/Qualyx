import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Qualyx Demo E-commerce App — Vite config (foundation only)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174
  }
});
