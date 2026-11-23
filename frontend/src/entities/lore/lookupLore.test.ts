import { describe, expect, it } from "vitest";
import { CARD_LORE } from "./cardLore";
import { lookupCardLore } from "./lookupLore";

describe("lookupCardLore", () => {
  it("puste pole i nieznana karta = null (UI nic nie pokazuje)", () => {
    expect(lookupCardLore("leader", "nie-ma-takiej-karty")).toBeNull();
    expect(lookupCardLore("agenda", null)).toBeNull();
    const [emptyId] = Object.entries(CARD_LORE.agenda).find(([, text]) => !text.trim()) ?? [];
    if (emptyId) expect(lookupCardLore("agenda", emptyId)).toBeNull();
  });

  it("szablon obejmuje aktywne karty każdego rodzaju", () => {
    for (const kind of Object.keys(CARD_LORE) as (keyof typeof CARD_LORE)[]) {
      expect(Object.keys(CARD_LORE[kind]).length).toBeGreaterThan(10);
    }
  });
});
