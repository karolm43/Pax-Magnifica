/*
 * Wspólne fixture'y E2E: `page` zbiera błędy JS i błędy konsoli, a test pada, jeśli jakiś wystąpił.
 * Dzięki temu każdy scenariusz przy okazji łapie wyjątki Reacta i nieudane żądania.
 */
import { test as base, expect, type Page } from "@playwright/test";

/*
 * Znane, nieszkodliwe komunikaty konsoli:
 * - ws-stomp: martwy socket STOMP z kodu odziedziczonego po AsyncTI4 (`useGameSocket`,
 *   `config.api.websocketUrl`), backend go nie obsługuje. Push stanu idzie przez `/bot/ws`.
 */
const IGNORED_CONSOLE = [/ws-stomp/];

export function watchErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (IGNORED_CONSOLE.some((re) => re.test(text))) return;
    errors.push(`console: ${text}`);
  });
  return errors;
}

export const test = base.extend<{ errors: string[] }>({
  // auto: działa w KAŻDYM teście, także gdy test nie prosi o `errors`.
  errors: [
    async ({ page }, use) => {
      const errors = watchErrors(page);
      await use(errors);
      expect(errors, "błędy JS / konsoli podczas testu").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };

/*
 * Włącza w ustawieniach (localStorage `ti4_settings`) opcję „Skip buttons” (Settings → Testing),
 * bez której ekran setupu nie pokazuje „Skip setup (random)”. Wołać PRZED `page.goto`.
 */
export async function enableSkipShortcuts(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const raw = localStorage.getItem("ti4_settings");
    const current = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
    localStorage.setItem("ti4_settings", JSON.stringify({ ...current, skipPhases: true }));
  });
}

/*
 * Kreator „Play → Me vs. bots": gracz 1 (host) gra wskazaną frakcją, pozostali to boty.
 * Kończy na planszy po pominięciu intro (okno setupu z tajnymi celami jest otwarte).
 */
export async function startSoloGame(page: Page, faction = "The Federation of Sol"): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await page.getByRole("button", { name: "Me vs. bots" }).click();
  await page.getByRole("button", { name: "Choose factions" }).click();
  // Kliknięcie w listę to tylko podgląd frakcji — wybór zatwierdza osobny przycisk.
  await page.getByRole("option", { name: faction }).click();
  await page.getByRole("button", { name: "Choose for player 1" }).click();
  await expect(page.getByRole("tab").first()).toContainText(faction);
  await page.getByRole("button", { name: "Seat & color" }).click();
  await page.getByRole("button", { name: "Start game" }).click();
  await page.getByRole("button", { name: "Skip" }).click();
  await expect(page).toHaveURL(/\/game$/);
}
