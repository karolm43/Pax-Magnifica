import { describe, expect, it } from "vitest";
import catalog from "../../../../assets/config/achievements.json";
import { ICONS } from "./AchievementCard";

describe("katalog osiągnięć (assets/config/achievements.json)", () => {
  it("każda ikona z pliku istnieje w mapie ICONS", () => {
    const missing = Object.entries(catalog.achievements)
      .filter(([, entry]) => !(entry.icon in ICONS))
      .map(([key]) => key);
    expect(missing).toEqual([]);
  });

  it("każdy tag jest jedną ze znanych kategorii", () => {
    const tags = new Set(["War", "Treachery", "Peace", "Race", "Empire", "Table"]);
    const bad = Object.entries(catalog.achievements)
      .filter(([, entry]) => !tags.has(entry.tag))
      .map(([key]) => key);
    expect(bad).toEqual([]);
  });
});
