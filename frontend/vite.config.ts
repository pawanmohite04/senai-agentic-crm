import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://backend:8000",
      "/dashboard": "http://backend:8000",
      "/threads": "http://backend:8000",
      "/analytics": "http://backend:8000",
      "/rag": "http://backend:8000",
      "/intelligence": "http://backend:8000",
      "/agent": "http://backend:8000",
      "/contacts": "http://backend:8000"
    }
  }
});
