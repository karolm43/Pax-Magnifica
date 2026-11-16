import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import { HERO_BOARD_FX, fxTargets } from "./heroBoardFx";

function tile(position: string, systemId: string, space: Record<string, string[]>, ground: Record<string, string[]> = {}): Tile {
  const units = (m: Record<string, string[]>) =>
    Object.fromEntries(
      Object.entries(m).map(([k, ids]) => [k, ids.map((entityId) => ({ entityId, entityType: "unit" as const, count: 1 }))]),
    );
  return {
    position,
    systemId,
    unitsByFaction: units(space),
    planets: { p: { unitsByFaction: units(ground) } },
    properties: { x: 0, y: 0 },
  } as unknown as Tile;
}

const tiles = [
  tile("000", "18", {}),
  tile("101", "27", { letnev: ["dn"] }),
  tile("102", "28", {}, { arborec: ["gf"] }),
  tile("103", "29", { arborec: ["cv"] }),
];

describe("fxTargets (RULES.md 64.4)", () => {
  it("statki / siły naziemne / Mecatol", () => {
    expect(fxTargets(HERO_BOARD_FX.letnevhero, tiles, { faction: "letnev", color: "red" }, null)).toEqual(["101"]);
    expect(fxTargets(HERO_BOARD_FX.arborechero, tiles, { faction: "arborec", color: "green" }, null)).toEqual(["102"]);
    expect(fxTargets(HERO_BOARD_FX.winnuhero, tiles, { faction: "winnu", color: "yellow" }, null)).toEqual(["000"]);
  });

  it("aktywny system, a bez niego systemy z jednostkami", () => {
    expect(fxTargets(HERO_BOARD_FX.hacanhero, tiles, { faction: "arborec", color: null }, "103")).toEqual(["103"]);
    expect(fxTargets(HERO_BOARD_FX.hacanhero, tiles, { faction: "arborec", color: null }, null)).toEqual(["102", "103"]);
  });

  it("każdy bohater z silnika ma przepis", () => {
    const engineHeroes = ["arborechero", "hacanhero", "jolnarhero", "letnevhero", "mentakhero", "sardakkhero", "solhero", "winnuhero", "yinhero"];
    expect(Object.keys(HERO_BOARD_FX).sort()).toEqual(engineHeroes);
  });
});
