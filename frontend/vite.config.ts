import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // En desarrollo, /api va al gateway publicado por docker-compose.dev.yml.
    proxy: { "/api": "http://localhost:18000" },
  },
  test: { environment: "jsdom" },
});
