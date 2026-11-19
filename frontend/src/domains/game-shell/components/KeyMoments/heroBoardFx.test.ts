import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import { HERO_BOARD_FX, coversForQueue, fxTargets, useHeroFx } from "./heroBoardFx";

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

  it("Xxekir Grom: systemy z PDS albo mechami bohatera", () => {
    const board = [tile("201", "30", {}, { xxcha: ["pd"] }), tile("202", "31", {}, { xxcha: ["gf"] }), tile("203", "32", {}, { xxcha: ["mf"] })];
    expect(fxTargets(HERO_BOARD_FX["xxchahero-te"], board, { faction: "xxcha", color: "green" }, null)).toEqual(["201", "203"]);
  });

  it("Nova Seed: kafel supernowej Muaat (po wymianie kafla), jeden", () => {
    const board = [tile("301", "81", { muaat: ["ws"] }), tile("302", "43", { muaat: ["ws"] })];
    expect(fxTargets(HERO_BOARD_FX.muaathero, board, { faction: "muaat", color: "orange" }, "302")).toEqual(["301"]);
  });

  it("zasłony kafli: z kolejki momentów, odsłonięcie po jednej pozycji", () => {
    const covers = coversForQueue([
      { kind: "breakthrough" },
      { kind: "hero", replaced: [{ position: "305", from: "26" }] },
    ]);
    expect(covers).toEqual({ "305": "26" });
    useHeroFx.getState().setCovers(covers);
    useHeroFx.getState().uncover("305");
    expect(useHeroFx.getState().covers).toEqual({});
    expect(HERO_BOARD_FX.muaathero.revealAt).toBeLessThan(HERO_BOARD_FX.muaathero.ms);
  });

  it("każdy bohater z silnika ma przepis", () => {
    const engineHeroes = ["arborechero", "argenthero", "hacanhero", "jolnarhero", "l1z1xhero", "letnevhero", "mentakhero", "muaathero", "naazhero", "saarhero", "sardakkhero", "solhero", "winnuhero", "xxchahero-te", "yinhero"];
    expect(Object.keys(HERO_BOARD_FX).sort()).toEqual(engineHeroes);
  });
});
