import { describe, expect, it } from "vitest";
import { CARD_LORE, LORE_ALIASES } from "./cardLore";
import { lookupCardLore } from "./lookupLore";

describe("lookupCardLore", () => {
  it("puste pole i nieznana karta = null (UI nic nie pokazuje)", () => {
    expect(lookupCardLore("leader", "nie-ma-takiej-karty")).toBeNull();
    expect(lookupCardLore("agenda", null)).toBeNull();
    const [emptyId] = Object.entries(CARD_LORE.agenda).find(([, text]) => !text.trim()) ?? [];
    if (emptyId) expect(lookupCardLore("agenda", emptyId)).toBeNull();
  });

  it("agenda Absol o tej samej nazwie czyta lore oficjalnej karty (alias)", () => {
    const aliases = LORE_ALIASES.agenda ?? {};
    expect(aliases["absol_mutiny"]).toBe("mutiny");
    expect(aliases["absol_leak"]).toBe("classified");
    for (const [absolId, officialId] of Object.entries(aliases)) {
      expect(CARD_LORE.agenda).toHaveProperty(officialId);
      expect(lookupCardLore("agenda", absolId)).toBe(lookupCardLore("agenda", officialId));
    }
    // nowe karty Absol mają własne pola
    expect(CARD_LORE.agenda).toHaveProperty("absol_pax");
    for (const n of [1, 2, 3, 4]) expect(CARD_LORE.agenda).toHaveProperty(`absol_emergency${n}`);
  });

  it("karty usunięte przez PoK/Codex/TE nie mają pól", () => {
    for (const gone of ["core_mining", "rt_biotic", "crown_of_thalnos", "representative_government"]) {
      expect(CARD_LORE.agenda).not.toHaveProperty(gone);
    }
    for (const gone of ["md_base", "md_c1", "x89_base", "x89", "iihq"]) {
      expect(CARD_LORE.technology).not.toHaveProperty(gone);
    }
    expect(CARD_LORE.leader).not.toHaveProperty("xxchahero");
    expect(CARD_LORE.leader).toHaveProperty("xxchahero-te");
  });

  it("szablon obejmuje aktywne karty każdego rodzaju", () => {
    for (const kind of Object.keys(CARD_LORE) as (keyof typeof CARD_LORE)[]) {
      expect(Object.keys(CARD_LORE[kind]).length).toBeGreaterThan(0);
    }
  });
});
