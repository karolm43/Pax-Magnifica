import { describe, expect, it } from "vitest";
import {
  afterFirstResearch,
  autoPay,
  autoSkips,
  compoundChoices,
  layoutColumns,
  remainingAfter,
  totalMissing,
  type ResearchOptions,
  type TechRow,
} from "./techModel";

const row = (over: Partial<TechRow>): TechRow => ({
  id: "x",
  name: "X",
  color: "BIOTIC",
  unitUpgrade: false,
  faction: null,
  baseUpgrade: null,
  prerequisites: [],
  missing: {},
  status: "available",
  ...over,
});

const options = (over: Partial<ResearchOptions>): ResearchOptions => ({
  breakthrough: null,
  tree: [],
  ownedColors: {},
  specialties: {},
  aida: false,
  relicSkips: [],
  planets: {},
  tradeGoods: 0,
  tradeGoodValue: 1,
  cost: 0,
  researched: [],
  discount: 0,
  compoundPlanets: {},
  asPrimary: false,
  second: null,
  ...over,
});

describe("techModel", () => {
  it("places techs in color columns by number of prerequisites", () => {
    const grid = layoutColumns([
      row({ id: "a", prerequisites: [] }),
      row({ id: "b", prerequisites: ["BIOTIC", "BIOTIC"] }),
      row({ id: "u", unitUpgrade: true, color: null }),
    ]);
    expect(grid.BIOTIC[0].map((r) => r.id)).toEqual(["a"]);
    expect(grid.BIOTIC[2].map((r) => r.id)).toEqual(["b"]);
    expect(grid.WARFARE.flat()).toEqual([]);
  });

  it("auto-picks the cheapest matching specialty planets", () => {
    const tech = row({ prerequisites: ["BIOTIC", "BIOTIC"], missing: { BIOTIC: 1 } });
    const opts = options({
      specialties: { rich: ["BIOTIC"], poor: ["BIOTIC"], red: ["WARFARE"] },
      planets: { rich: 3, poor: 1, red: 0 },
    });
    const { skips, left } = autoSkips(tech, opts);
    expect(skips).toEqual(["poor"]);
    expect(totalMissing(left)).toBe(0);
    expect(totalMissing(remainingAfter(tech, ["red"], opts))).toBe(1);
  });

  it("uses AI Development Algorithm only for unit upgrades", () => {
    const upgrade = row({ unitUpgrade: true, color: null, missing: { WARFARE: 1 } });
    expect(autoSkips(upgrade, options({ aida: true })).skips).toEqual(["aida"]);
    const colored = row({ missing: { WARFARE: 1 } });
    expect(autoSkips(colored, options({ aida: true })).skips).toEqual([]);
  });

  it("pays without redundant planets and tops up with trade goods", () => {
    expect(autoPay({ a: 4, b: 2, c: 1 }, [], 0, 6)).toEqual({ planets: ["a", "b"], tradeGoods: 0 });
    expect(autoPay({ a: 4 }, [], 5, 6)).toEqual({ planets: ["a"], tradeGoods: 2 });
    expect(autoPay({ a: 4 }, ["a"], 5, 4)).toEqual({ planets: [], tradeGoods: 4 });
    expect(autoPay({ a: 4 }, [], 5, 0)).toEqual({ planets: [], tradeGoods: 0 });
  });

  it("Specialist Compounds: only planets of the technology's color pay, never for upgrades", () => {
    const opts = options({ cost: 6, compoundPlanets: { a: ["BIOTIC"], b: ["WARFARE"] } });
    expect(compoundChoices(row({ color: "BIOTIC" }), opts, [])).toEqual(["a"]);
    expect(compoundChoices(row({ color: "BIOTIC" }), opts, ["a"])).toEqual([]);
    expect(compoundChoices(row({ unitUpgrade: true, color: null }), opts, [])).toEqual([]);
    expect(compoundChoices(row({ color: "BIOTIC" }), { ...opts, cost: 0 }, [])).toEqual([]);
  });

  it("Brilliant: the first research counts towards the second one's prerequisites", () => {
    const second = options({
      cost: 6,
      tree: [
        row({ id: "first", color: "BIOTIC" }),
        row({ id: "next", color: "BIOTIC", missing: { BIOTIC: 1 }, status: "locked" }),
      ],
    });
    const after = afterFirstResearch(second, "first");
    expect(after.tree.find((r) => r.id === "first")?.status).toBe("owned");
    expect(after.tree.find((r) => r.id === "next")?.status).toBe("available");
    expect(after.ownedColors.BIOTIC).toBe(1);
  });
});
