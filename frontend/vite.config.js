import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        // Local default: API on same machine. Docker UI uses nginx → backend service.
        target: process.env.VITE_API_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
