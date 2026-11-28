import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import {
  HERO_BOARD_FX,
  TOKEN_BOARD_FX,
  coversForQueue,
  fxTargets,
  neighborTiles,
  useHeroFx,
} from "./heroBoardFx";

function tile(
  position: string,
  systemId: string,
  space: Record<string, string[]>,
  ground: Record<string, string[]> = {},
  at: { x: number; y: number; planet?: string } = { x: 0, y: 0 },
): Tile {
  const units = (m: Record<string, string[]>) =>
    Object.fromEntries(
      Object.entries(m).map(([k, ids]) => [k, ids.map((entityId) => ({ entityId, entityType: "unit" as const, count: 1 }))]),
    );
  return {
    position,
    systemId,
    unitsByFaction: units(space),
    planets: { [at.planet ?? "p"]: { unitsByFaction: units(ground) } },
    properties: { x: at.x, y: at.y },
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

  it("Dimensional Anchor: wir w systemach z dokami Cabal (Dimensional Tear), nie z jednostkami", () => {
    const board = [
      tile("401", "30", { cabal: ["cv"] }),
      tile("402", "31", {}, { cabal: ["sd", "gf"] }),
      tile("403", "32", { cabal: ["sd"] }),
    ];
    expect(HERO_BOARD_FX.cabalhero.mark).toBe("maw");
    expect(fxTargets(HERO_BOARD_FX.cabalhero, board, { faction: "cabal", color: "red" }, null)).toEqual(["402", "403"]);
  });

  it("macki Cabal: sąsiedzi z siatki heksów (rozstaw 260/300)", () => {
    const mid = tile("000", "18", {}, {}, { x: 500, y: 500 });
    const board = [
      mid,
      tile("101", "1", {}, {}, { x: 500, y: 200 }),
      tile("102", "2", {}, {}, { x: 760, y: 350 }),
      tile("201", "3", {}, {}, { x: 500, y: -100 }),
    ];
    expect(neighborTiles(board, mid).map((t) => t.position)).toEqual(["101", "102"]);
  });

  it("Geoform: system planety z kartą bohatera (Elysium)", () => {
    const board = [
      tile("501", "4", {}, { titans: ["pd"] }),
      tile("502", "5", {}, {}, { x: 0, y: 0, planet: "elysium" }),
    ];
    const owner = { faction: "titans", color: "pink", planets: ["elysium"] };
    expect(fxTargets(HERO_BOARD_FX.titanshero, board, owner, null)).toEqual(["502"]);
  });

  it("miejsca działania (fakty area): Sol — systemy, z których zniknęły jego żetony", () => {
    const board = [tile("601", "6", { sol: ["cv"] }), tile("602", "7", {}), tile("603", "8", {})];
    const owner = {
      faction: "sol",
      color: "blue",
      areas: [
        { position: "602", self: true, kind: "token_removed" as const },
        { position: "603", self: false, kind: "token_removed" as const },
      ],
    };
    expect(fxTargets(HERO_BOARD_FX.solhero, board, owner, null)).toEqual(["602"]);
    // Bez faktów area — zapasowy cel przepisu (systemy z jednostkami).
    expect(fxTargets(HERO_BOARD_FX.solhero, board, { faction: "sol", color: "blue" }, null)).toEqual(["601"]);
  });

  it("Saar: system, w którym rywale stracili piechotę i myśliwce", () => {
    const board = [tile("701", "9", {}, { saar: ["sd"] }), tile("702", "10", { other: ["ff"] })];
    const owner = { faction: "saar", color: "brown", areas: [{ position: "702", self: false, kind: "loss" as const }] };
    expect(fxTargets(HERO_BOARD_FX.saarhero, board, owner, null)).toEqual(["702"]);
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

  it("Singularity Reactor: both swapped systems, own rift mark, reveal under the flash", () => {
    const board = [tile("801", "26", {}), tile("802", "25", { ghost: ["dd"] }), tile("803", "19", { ghost: ["cv"] })];
    const owner = {
      faction: "ghost",
      color: "blue",
      replaced: [
        { position: "801", from: "25" },
        { position: "802", from: "26" },
      ],
    };
    const recipe = HERO_BOARD_FX.ghosthero;
    expect(recipe.mark).toBe("rift");
    expect(fxTargets(recipe, board, owner, null)).toEqual(["801", "802"]);
    expect(recipe.flashAt).toBeDefined();
    expect(recipe.revealAt).toBeGreaterThanOrEqual(recipe.flashAt ?? 0);
    expect(recipe.revealAt).toBeLessThan(recipe.ms);
    expect(recipe.sounds?.length).toBeGreaterThan(3);
  });

  it("Creuss wormhole token: the opened system, one recipe per token in its colour", () => {
    const board = [tile("901", "19", {}), tile("902", "20", {})];
    const owner = {
      faction: "ghost",
      color: "blue",
      areas: [
        { position: "902", self: true, kind: "gain" as const },
        { position: "901", self: true, kind: "loss" as const },
      ],
    };
    expect(Object.keys(TOKEN_BOARD_FX).sort()).toEqual(["creussalpha", "creussbeta", "creussgamma", "whdelta"]);
    expect(fxTargets(TOKEN_BOARD_FX.creussbeta, board, owner, null)).toEqual(["902"]);
    expect(new Set(Object.values(TOKEN_BOARD_FX).map((r) => r.tone)).size).toBe(4);
    expect(TOKEN_BOARD_FX.creussalpha.mark).toBe("portal");
  });

  it("każdy bohater z silnika ma przepis", () => {
    const engineHeroes = ["arborechero", "argenthero", "cabalhero", "empyreanhero", "ghosthero", "hacanhero", "jolnarhero", "l1z1xhero", "letnevhero", "mahacthero", "mentakhero", "muaathero", "naaluhero", "naazhero", "nekrohero", "nomadhero", "saarhero", "sardakkhero", "solhero", "titanshero", "winnuhero", "xxchahero-te", "yinhero", "yssarilhero"];
    expect(Object.keys(HERO_BOARD_FX).sort()).toEqual(engineHeroes);
  });
});
