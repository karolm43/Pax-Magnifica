/*
 * Narzędzia stołu: zoom mapy (Ctrl + kółko, klawisze) oraz zgłoszenie błędu („Report bug")
 * ze zrzutem ekranu, zapisywane przez backend w katalogu raportów hosta.
 */
import { expect, startSoloGame, test } from "./fixtures";

test.beforeEach(async ({ page }) => {
  // Diagnostyka: odrzucone żądania backendu trafiają do logu testu (łatwiej znaleźć źródło).
  page.on("response", (r) => {
    if (r.status() >= 400) console.log("HTTP", r.status(), r.request().method(), r.url());
  });
  await startSoloGame(page);
  await page.getByRole("button", { name: "Skip setup (random)" }).click();
  await expect(page.getByRole("heading", { name: "Strategy Phase" })).toBeVisible();
});

test("Ctrl + kółko i klawisze +/-/0 zmieniają zoom mapy", async ({ page }) => {
  const label = page.getByText(/^\d+%$/).first();
  const before = Number((await label.innerText()).replace("%", ""));

  // Kursor nad planszą, poza panelami i wachlarzem kart strategii.
  await page.mouse.move(1300, 700);
  await page.keyboard.down("Control");
  await page.mouse.wheel(0, -100);
  await page.keyboard.up("Control");
  await expect(label).not.toHaveText(`${before}%`);
  const zoomedIn = Number((await label.innerText()).replace("%", ""));
  expect(zoomedIn).toBeGreaterThan(before);

  await page.keyboard.press("-");
  await expect(label).toHaveText(`${before}%`);
  await page.keyboard.press("0"); // dopasuj planszę — zoom ze szczebla drabinki
  await expect(label).toHaveText(/^\d+%$/);
});

test("Report bug: zrzut + opis trafia do hosta", async ({ page }) => {
  await page.getByRole("button", { name: "Report bug" }).click();
  const dialog = page.getByRole("dialog", { name: "Report a bug" });
  await expect(dialog).toBeVisible({ timeout: 30_000 });
  await expect(dialog.getByRole("img", { name: "Screenshot of your view" })).toBeVisible();
  await expect(dialog.getByRole("checkbox", { name: "Attach this screenshot" })).toBeChecked();

  const send = dialog.getByRole("button", { name: "Send report" });
  await dialog.getByRole("textbox", { name: "What went wrong?" }).fill("E2E: test zgłoszenia");
  await send.click();
  await expect(dialog.getByRole("status")).toContainText("Report sent");
  await dialog.getByRole("button", { name: "Close", exact: true }).last().click();
  await expect(dialog).toBeHidden();
});
