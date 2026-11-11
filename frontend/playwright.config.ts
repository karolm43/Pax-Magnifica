/*
 * Testy E2E (Playwright): prawdziwa przeglądarka klika po aplikacji.
 *
 * Uruchomienie (w frontend/):  npm run e2e        — headless
 *                              npm run e2e:ui     — okno z podglądem kroków (debug)
 *
 * Playwright sam stawia DWA osobne serwery, odizolowane od gry użytkownika:
 *   - backend  :8100 — scripts/e2e_server.py (pusty stan, zapis w pamięci, saves/ nietknięte),
 *   - frontend :5273 — Vite z proxy na :8100 (zmienna CUSTODIAN_BACKEND).
 * Gra na :8000/:5173 może w tym czasie działać — testy jej nie dotykają.
 *
 * Pliki testów: e2e/*.e2e.ts (inne rozszerzenie niż *.test.ts, żeby Vitest ich nie zbierał).
 */
import { defineConfig, devices } from "@playwright/test";

const BACKEND_PORT = 8100;
const FRONTEND_PORT = 5273;

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  // Backend trzyma JEDEN stan gry — testy w jednym przebiegu idą po kolei, nie równolegle.
  workers: 1,
  fullyParallel: false,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    viewport: { width: 1600, height: 900 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1600, height: 900 } } }],
  webServer: [
    {
      command: `uv run python scripts/e2e_server.py --port ${BACKEND_PORT}`,
      cwd: "..",
      url: `http://127.0.0.1:${BACKEND_PORT}/docs`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npx vite --port ${FRONTEND_PORT} --strictPort`,
      url: `http://localhost:${FRONTEND_PORT}/`,
      env: { CUSTODIAN_BACKEND: `http://127.0.0.1:${BACKEND_PORT}` },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
