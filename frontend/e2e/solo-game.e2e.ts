/*
 * Scenariusze dymne gry solo (człowiek + 5 botów): od menu do fazy strategii.
 * Backend E2E żyje przez cały przebieg, ale każdy scenariusz zaczyna NOWĄ grę z menu,
 * więc stan poprzedniego testu nie przeszkadza.
 */
import { expect, startSoloGame, test } from "./fixtures";

test("menu startowe ładuje się bez błędów", async ({ page }) => {
  await page.goto("/");
  for (const name of ["Play", "Load game", "Settings", "How to play", "Rules"]) {
    await expect(page.getByRole("button", { name, exact: true })).toBeVisible();
  }
});

test("setup przeklikany ręcznie: tajny cel → Custodians → cele publiczne → faza strategii", async ({
  page,
}) => {
  await startSoloGame(page);
  const setup = page.getByRole("dialog", { name: "Game setup" });

  // 1. Tajne cele: boty wybrały od razu, człowiek wybiera jeden z dwóch.
  await expect(setup.getByRole("heading", { name: "Secret objectives" })).toBeVisible();
  const keep = setup.getByRole("button", { name: "Keep this objective" });
  await expect(keep).toBeDisabled();
  await setup.getByRole("button", { name: /Secret objective ·/ }).first().click();
  await expect(keep).toBeEnabled();
  await keep.click();

  // 2. Wszyscy wybrali → mówca (tu: człowiek) kładzie żeton Custodians na Mecatol Rex.
  await expect(setup.getByRole("heading", { name: "Custodians token" })).toBeVisible();
  await setup.getByRole("button", { name: "Place on Mecatol Rex" }).click();

  // 3. Cele publiczne: mówca odkrywa dwa pierwsze cele Etapu I.
  await expect(setup.getByRole("heading", { name: "Public objectives" })).toBeVisible();
  await setup.getByRole("button", { name: /Reveal two Stage I objectives/ }).click();
  await expect(setup.getByRole("region", { name: "Stage I objectives" })).toContainText("1 VP");
  await setup.getByRole("button", { name: "Begin the Strategy Phase" }).click();

  await expect(setup).toBeHidden();
  await expect(page.getByRole("heading", { name: "Strategy Phase" })).toBeVisible();
});

test("Skip setup (random) też kończy w fazie strategii", async ({ page }) => {
  await startSoloGame(page);
  await page.getByRole("button", { name: "Skip setup (random)" }).click();
  await expect(page.getByRole("dialog", { name: "Game setup" })).toBeHidden();
  await expect(page.getByRole("heading", { name: "Strategy Phase" })).toBeVisible();
});
