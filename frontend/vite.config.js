import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The React dev server proxies API calls to FastAPI, so the browser only talks to one origin (no CORS).
const API_TARGET = "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/repos": API_TARGET,
      "/jobs": API_TARGET,
      "/health": API_TARGET,
    },
  },
});
