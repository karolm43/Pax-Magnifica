import { describe, expect, it } from "vitest";
import {
  fanSourceBadge,
  gameVariantIds,
  isInGameDeck,
  toggleVariant,
  variantModules,
} from "./officialSources";
import { agendaPool, relicPool } from "@/domains/cards/model/cardPoolBrowser";

const moduleOf = (id: string) => {
  const found = variantModules().find((m) => m.id === id);
  if (!found) throw new Error(`missing variant module ${id}`);
  return found;
};

function poolAliases(groups: ReturnType<typeof relicPool>): string[] {
  return groups.flatMap((g) => g.entries.map((e) => e.alias));
}

describe("moduły wariantów gry (assets/config/variants.json)", () => {
  it("lista modułów pochodzi z manifestu (Absol: agendy i relikty)", () => {
    const ids = variantModules().map((m) => m.id);
    expect(ids).toEqual(expect.arrayContaining(["absol_agendas", "absol_relics"]));
    expect(fanSourceBadge("absol")).toBe("ABS");
    expect(fanSourceBadge("pok")).toBeNull();
  });

  it("gameVariantIds: nowe gry niosą variants, stare tylko agendaVariant", () => {
    expect(gameVariantIds({ variants: ["absol_relics"] })).toEqual(["absol_relics"]);
    expect(gameVariantIds({ agendaVariant: "absol" })).toEqual(["absol_agendas"]);
    expect(gameVariantIds({ agendaVariant: "standard" })).toEqual([]);
    expect(gameVariantIds(undefined)).toEqual([]);
  });

  it("talia reliktów gry z modułem Absol = karty Absol, bez modułu = oficjalne", () => {
    const official = poolAliases(relicPool());
    const absol = poolAliases(relicPool(["absol_relics"]));
    expect(official.some((a) => a.startsWith("absol_"))).toBe(false);
    expect(absol).toHaveLength(20);
    expect(absol.every((a) => a.startsWith("absol_"))).toBe(true);
    expect(isInGameDeck("relic", "absol_codex", "absol", ["absol_relics"])).toBe(true);
    expect(isInGameDeck("relic", "absol_codex", "absol")).toBe(false);
  });

  it("moduł reliktów nie zmienia talii agend", () => {
    const standard = agendaPool().flatMap((g) => g.entries.map((e) => e.alias));
    const withRelics = agendaPool(["absol_relics"]).flatMap((g) => g.entries.map((e) => e.alias));
    expect(withRelics).toEqual(standard);
  });

  it("toggleVariant dodaje/zdejmuje moduł i nie łączy dwóch całych talii tego samego typu", () => {
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
    const rival = { ...agendas, id: "rival_agendas" };
    expect(toggleVariant(["absol_agendas"], rival, true)).toEqual(["rival_agendas"]);
  });
});
