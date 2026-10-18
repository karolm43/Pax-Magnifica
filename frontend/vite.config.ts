import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev-serwer Vite na :5173. Zapytania API są kierowane do backendu FastAPI
// (:8000) przez proxy, dzięki czemu frontend łączy się z adresami względnymi
// (/api, /ws) bez twardego kodowania hosta backendu.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
      // Grafiki kafelków i inne assety statyczne serwuje backend pod /static.
      "/static": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
