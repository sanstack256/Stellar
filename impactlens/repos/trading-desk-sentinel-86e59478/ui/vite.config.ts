import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/truforge-api": {
        // Point to the mock TrueForge server. Switch to http://127.0.0.1:8790
        // once a real model provider is configured in the live TrueForge instance.
        target: process.env.TRUEFORGE_BASE_URL ?? "http://127.0.0.1:8792",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/truforge-api/, ""),
      },
    },
  },
});
