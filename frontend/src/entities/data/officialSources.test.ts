import { afterEach, describe, expect, it } from "vitest";
import {
  fanSourceBadge,
  gameVariantIds,
  isInGameDeck,
  selectedModulesReplace,
  toggleVariant,
  variantModules,
} from "./officialSources";
import { actionCardPool, relicPool } from "@/domains/cards/model/cardPoolBrowser";
import { setVariantData, withVariant } from "@/entities/lookup/variantData";
import { getTechData } from "@/entities/lookup/tech";

const moduleOf = (id: string) => {
  const found = variantModules().find((m) => m.id === id);
  if (!found) throw new Error(`missing variant module ${id}`);
  return found;
};

function poolAliases(groups: ReturnType<typeof relicPool>): string[] {
  return groups.flatMap((g) => g.entries.map((e) => e.alias));
}

afterEach(() => setVariantData(null));

describe("moduły wariantów gry (assets/config/variants.json)", () => {
  it("lista modułów do Ustawień pochodzi z manifestu", () => {
    const ids = variantModules().map((m) => m.id);
    expect(ids).toEqual(
      expect.arrayContaining(["absol_agendas", "absol_relics", "bsp_factions"]),
    );
    expect(fanSourceBadge("absol")).toBe("ABS");
    expect(fanSourceBadge("pok")).toBeNull();
  });

  it("gameVariantIds: nowe gry niosą variants, stare tylko agendaVariant", () => {
    expect(gameVariantIds({ variants: ["absol_relics"] })).toEqual(["absol_relics"]);
    expect(gameVariantIds({ agendaVariant: "absol" })).toEqual(["absol_agendas"]);
    expect(gameVariantIds({ agendaVariant: "standard" })).toEqual([]);
    expect(gameVariantIds(undefined)).toEqual([]);
  });

  it("errata z backendu podmienia tekst komponentu pod oficjalnym id", () => {
    const official = getTechData("st");
    expect(official).toBeDefined();
    setVariantData({
      variants: ["bsp_factions"],
      badges: { black_spectrum: "BSP" },
      entries: {
        technologies: { st: { alias: "st", text: "BSP text", variantSource: "black_spectrum" } },
      },
      decks: {},
    });
    expect(getTechData("st")?.text).toBe("BSP text");
    expect(getTechData("st")?.name).toBe(official?.name);
    expect(fanSourceBadge("black_spectrum")).toBe("BSP");
    expect(withVariant("relics", "codex", undefined)).toBeUndefined();
  });

  it("talia zastąpiona przez moduł: pula = karty z backendu, także nowe spoza danych frontu", () => {
    const official = poolAliases(relicPool());
    expect(official.some((a) => a.startsWith("absol_"))).toBe(false);
    setVariantData({
      variants: ["bsp_cards"],
      badges: {},
      entries: {
        action_cards: {
          bsp_new: { alias: "bsp_new", name: "Brand New", text: "x", source: "black_spectrum" },
        },
      },
      decks: { relic: ["absol_codex"], actionCard: ["bsp_new", "sabotage1"] },
    });
    expect(poolAliases(relicPool())).toEqual(["absol_codex"]);
    expect(poolAliases(actionCardPool())).toContain("bsp_new");
    expect(isInGameDeck("relic", "codex", "pok")).toBe(false);
  });

  it("toggleVariant nie łączy dwóch całych talii tego samego typu", () => {
    const relics = moduleOf("absol_relics");
    const agendas = moduleOf("absol_agendas");
    expect(toggleVariant([], relics, true)).toEqual(["absol_relics"]);
    expect(toggleVariant(["absol_relics"], agendas, true)).toEqual([
      "absol_relics",
      "absol_agendas",
    ]);
    expect(toggleVariant(["absol_relics", "absol_agendas"], relics, false)).toEqual([
      "absol_agendas",
    ]);
    expect(toggleVariant(["absol_relics"], moduleOf("bsp_cards"), true)).toEqual(["bsp_cards"]);
  });

  it("selectedModulesReplace: ploty Black Spectrum w wyborze frakcji", () => {
    expect(selectedModulesReplace(["bsp_firmament_plots"], "genericcards", "black_spectrum")).toBe(
      true,
    );
    expect(selectedModulesReplace(["absol_relics"], "genericcards", "black_spectrum")).toBe(false);
  });
});
