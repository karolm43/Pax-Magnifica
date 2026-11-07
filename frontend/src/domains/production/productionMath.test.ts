import { describe, expect, it } from "vitest";
import {
  autoPay,
  bumpCart,
  cartCost,
  fundsTotal,
  maxMore,
  whyNotAdd,
} from "./productionMath";
import type {
  ProductionBody,
  ProductionPlanet,
  ProductionUnit,
} from "./useProduction";

const planet = (id: string, resources: number, exhausted = false): ProductionPlanet => ({
  planet: id,
  name: id,
  position: "000",
  resources,
  influence: 0,
  planetType: null,
  exhausted,
  inActiveSystem: true,
});

const unit = (over: Partial<ProductionUnit>): ProductionUnit => ({
  baseType: "cruiser",
  asyncId: "ca",
  name: "Cruiser",
  cost: 2,
  unitsPerCost: 1,
  placement: "space",
  reinforcements: 8,
  ...over,
});

const infantry = unit({
  baseType: "infantry",
  asyncId: "gf",
  name: "Infantry",
  cost: 1,
  unitsPerCost: 2,
  placement: "planet",
  reinforcements: null,
});

const view = (over: Partial<ProductionBody> = {}): ProductionBody => ({
  active: true,
  position: "000",
  playerId: "p1",
  faction: "sol",
  limit: 6,
  used: 0,
  remaining: 6,
  blockaded: false,
  producers: [],
  groundZones: ["jord"],
  planets: [planet("jord", 4), planet("spent", 3, true)],
  tradeGoods: 1,
  units: [unit({}), infantry],
  ...over,
});

describe("cartCost", () => {
  it("łączy piechotę z różnych stref w pary", () => {
    let cart = bumpCart([], "infantry", "jord", 1);
    cart = bumpCart(cart, "infantry", "other", 1);
    expect(cartCost([infantry], cart)).toBe(1);
  });
  it("nieparzysta liczba płaci pełną parę", () => {
    expect(cartCost([infantry], bumpCart([], "infantry", "jord", 3))).toBe(2);
  });
});

describe("autoPay", () => {
  it("bierze planety, TG tylko na resztę", () => {
    const planets = [planet("a", 4), planet("b", 2)];
    expect(autoPay(planets, 5, 4)).toEqual({ planets: ["a"], tradeGoods: 0 });
    expect(autoPay(planets, 5, 7)).toEqual({ planets: ["a", "b"], tradeGoods: 1 });
  });
  it("pomija wyczerpane planety", () => {
    expect(autoPay([planet("x", 5, true)], 3, 2)).toEqual({ planets: [], tradeGoods: 2 });
  });
});

describe("limity", () => {
  it("zasoby = gotowe planety + TG", () => {
    expect(fundsTotal(view())).toBe(5);
  });
  it("blokada odcina statki, nie siły naziemne", () => {
    const v = view({ blockaded: true });
    expect(whyNotAdd(v, [], v.units[0], null)).toMatch(/Blockaded/);
    expect(whyNotAdd(v, [], infantry, "jord")).toBeNull();
  });
  it("maxMore uwzględnia zasoby i sloty", () => {
    const v = view();
    expect(maxMore(v, [], v.units[0], null)).toBe(2); // 5 zasobów / koszt 2
    expect(maxMore(v, [], infantry, "jord")).toBe(6); // 3 pary, ale limit 6 sztuk
  });
  it("siły naziemne wymagają strefy z producentem", () => {
    const v = view();
    expect(whyNotAdd(v, [], infantry, "nowhere")).toMatch(/No place/);
  });
});
