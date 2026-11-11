/// <reference types="vitest/config" />
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

const ReactCompilerConfig = {
  target: "19",
};

/*
 * Rollup's property-path tree-shaking spends ~5 minutes analysing react-dom's single-file
 * production bundle (89% of the build), only to keep nearly all of it. Including React whole
 * cuts the build to ~1 minute with byte-identical output.
 */
/*
 * Adres backendu dla proxy. Domyślnie gra użytkownika (:8000); testy E2E (Playwright) podają
 * CUSTODIAN_BACKEND=http://127.0.0.1:8100 i dostają osobny, świeży backend (scripts/e2e_server.py).
 */
const backend = process.env.CUSTODIAN_BACKEND ?? "http://127.0.0.1:8000";

const includeReactWhole: Plugin = {
  name: "include-react-whole",
  enforce: "post",
  transform(code, id) {
    if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) {
      return { code, map: null, moduleSideEffects: "no-treeshake" };
    }
  },
};

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [["babel-plugin-react-compiler", ReactCompilerConfig]],
      },
    }),
    includeReactWhole,
  ],
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
    },
  },
  assetsInclude: ["**/*.woff", "**/*.woff2", "**/*.ttf", "**/*.otf"],
  server: {
    // Gra sieciowa (RULES.md 44.6): nasłuch na wszystkich interfejsach, żeby znajomi z ZeroTier/LAN
    // weszli na http://<IP-hosta>:5173. Bezpieczne: dopóki host nie otworzy lobby, backend
    // obsługuje WYŁĄCZNIE ten komputer (rozpoznaje go po X-Forwarded-For dopisanym przez proxy).
    host: true,
    proxy: {
      // Custodian Engine backend (FastAPI). "/bot/api/..." -> "/api/..." na :8000.
      "/bot": {
        target: backend,
        changeOrigin: true,
        // WebSocket /bot/ws -> /ws (push stanu w grze sieciowej, RULES.md 44.3).
        ws: true,
        // X-Forwarded-For z adresem klienta — backend odróżnia hosta od gości (RULES.md 44.6).
        xfwd: true,
        rewrite: (path) => path.replace(/^\/bot/, ""),
      },
      // Statyczne assety (grafiki kafelków/jednostek) serwowane przez backend.
      "/static": {
        target: backend,
        changeOrigin: true,
        xfwd: true,
      },
    },
  },
  // Konfiguracja testów (Vitest): środowisko jsdom dla komponentów React (RTL),
  // globalne API testowe (describe/it/expect) oraz plik setupu z matcherami jest-dom.
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    // Zestaw testowy dopiero powstaje (zadania 8.4/11.x) — brak plików testowych
    // nie jest błędem na tym etapie infrastruktury.
    passWithNoTests: true,
  },
});
