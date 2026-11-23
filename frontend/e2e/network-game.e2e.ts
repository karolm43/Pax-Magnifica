/*
 * Gra sieciowa w dwóch przeglądarkach naraz (RULES.md 44.x, 45.3): host + gość.
 *
 * Gość wchodzi linkiem z panelu „Invite friends" (adres LAN/ZeroTier tego komputera),
 * więc backend widzi INNY adres niż loopback i traktuje go jak gościa — tak jak u znajomego.
 * Bez interfejsu sieciowego (brak linku w panelu) test jest pomijany.
 */
import type { Page } from "@playwright/test";
import { expect, test, watchErrors } from "./fixtures";

async function hostLobbyFor2(page: Page): Promise<string | null> {
  await page.goto("/");
  await page.getByRole("button", { name: "Play", exact: true }).click();
  await page.getByRole("radio", { name: "2", exact: true }).click();
  const links = page.locator("code");
  if ((await links.count()) === 0) return null;
  return (await links.first().textContent())?.trim() ?? null;
}

test("host + gość: lobby na żywo, każdy wybiera frakcję, wspólny start i tajne cele", async ({
  page: host,
  browser,
}) => {
  test.setTimeout(120_000);
  const link = await hostLobbyFor2(host);
  test.skip(!link, "Brak adresu LAN/ZeroTier — gość nie odróżni się od hosta.");

  const guestContext = await browser.newContext();
  const guest = await guestContext.newPage();
  const guestErrors = watchErrors(guest);

  // Gość dołącza; host widzi go w lobby na żywo (push przez WebSocket).
  await guest.goto(link!);
  await guest.getByRole("textbox", { name: "Your name" }).fill("Gosc");
  await guest.getByRole("button", { name: "Join lobby" }).click();
  await expect(guest.getByText(/Gosc \(you\)/).first()).toBeVisible();
  await expect(host.getByText(/Gosc · joined/).first()).toBeVisible();
  // Ustawienia partii należą do hosta.
  await expect(guest.getByRole("button", { name: "Choose factions" })).toBeDisabled();

  // Krok frakcji: każdy wybiera swoją, drugi widzi to od razu.
  await host.getByRole("button", { name: "Choose factions" }).click();
  await host.getByRole("option", { name: "The Federation of Sol" }).click();
  await host.getByRole("button", { name: "Choose for player 1" }).click();
  await expect(guest.getByRole("tab").first()).toContainText("The Federation of Sol");

  await guest.getByRole("option", { name: "The Emirates of Hacan" }).click();
  await guest.getByRole("button", { name: "Choose for player 2" }).click();
  await expect(host.getByRole("tab").nth(1)).toContainText("The Emirates of Hacan");

  // Start: tylko host prowadzi kreator dalej.
  await host.getByRole("button", { name: "Choose colors" }).click();
  await host.getByRole("button", { name: "Start game" }).click();

  // Obaj dostają intro i trafiają do wyboru tajnych celów — równocześnie, każdy swoje karty.
  for (const page of [host, guest]) {
    await page.getByRole("button", { name: "Skip" }).click();
    await expect(page).toHaveURL(/\/game$/);
    const setup = page.getByRole("dialog", { name: "Game setup" });
    await expect(setup.getByRole("heading", { name: "Secret objectives" })).toBeVisible();
    await setup.getByRole("button", { name: /Secret objective ·/ }).first().click();
    await setup.getByRole("button", { name: "Keep this objective" }).click();
  }

  // Obaj wybrali → setup idzie dalej u obu (krok Custodians).
  for (const page of [host, guest]) {
    await expect(page.getByRole("heading", { name: "Custodians token" })).toBeVisible();
  }

  expect(guestErrors, "błędy JS / konsoli u gościa").toEqual([]);
  await guestContext.close();
});
