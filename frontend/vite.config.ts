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
    proxy: {
      // Custodian Engine backend (FastAPI). "/bot/api/..." -> "/api/..." na :8000.
      "/bot": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/bot/, ""),
      },
      // Statyczne assety (grafiki kafelków/jednostek) serwowane przez backend.
      "/static": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
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
