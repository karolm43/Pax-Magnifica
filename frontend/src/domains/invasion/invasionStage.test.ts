import { describe, expect, it } from "vitest";
import {
  bombardList,
  bumpStage,
  defaultBombardPlan,
  landAll,
  remainingOf,
  shiftBombard,
  stageList,
  stageTotal,
} from "./invasionStage";
import type { BombardGroup, InvasionUnit } from "./useInvasion";

const cargo: InvasionUnit[] = [
  {
    baseType: "infantry",
    asyncId: "gf",
    name: "Infantry",
    count: 4,
    damaged: 0,
    sustain: false,
    baseHitsOn: 8,
  },
  {
    baseType: "mech",
    asyncId: "mf",
    name: "Mech",
    count: 1,
    damaged: 0,
    sustain: true,
    baseHitsOn: 6,
  },
];

const dread: BombardGroup = {
  baseType: "dreadnought",
  asyncId: "dn",
  name: "Dreadnought",
  count: 3,
  hitsOn: 5,
  dicePerUnit: 1,
  expectedHits: 1.5,
};

describe("lądowanie", () => {
  it("nie pozwala zlądować więcej, niż jest w przestrzeni", () => {
    let stage = bumpStage({}, cargo, "a", "infantry", 3);
    stage = bumpStage(stage, cargo, "b", "infantry", 5);
    expect(stage).toEqual({ a: { infantry: 3 }, b: { infantry: 1 } });
    expect(remainingOf(cargo, stage, "infantry")).toBe(0);
  });

  it("zmniejszenie do zera usuwa wpis planety", () => {
    const stage = bumpStage(
      bumpStage({}, cargo, "a", "mech", 1),
      cargo,
      "a",
      "mech",
      -3,
    );
    expect(stage).toEqual({});
  });

  it("„land all” ląduje wszystko na jednej planecie", () => {
    const stage = landAll({}, cargo, "a");
    expect(stage).toEqual({ a: { infantry: 4, mech: 1 } });
    expect(stageTotal(stage)).toBe(5);
    expect(stageList(stage)).toContainEqual({
      planet: "a",
      baseType: "mech",
      count: 1,
    });
  });
});

describe("bombardowanie", () => {
  const targets = ["a", "b"];

  it("domyślnie wszystko na pierwszy cel", () => {
    expect(defaultBombardPlan([dread], targets)).toEqual({
      dreadnought: { a: 3 },
    });
  });

  it("przesuwanie zachowuje sumę równą liczbie statków", () => {
    let plan = defaultBombardPlan([dread], targets);
    plan = shiftBombard(plan, dread, targets, "b", 1);
    plan = shiftBombard(plan, dread, targets, "b", 1);
    expect(plan.dreadnought).toEqual({ a: 1, b: 2 });
    plan = shiftBombard(plan, dread, targets, "b", -1);
    expect(plan.dreadnought).toEqual({ a: 2, b: 1 });
    expect(bombardList(plan)).toEqual([
      { baseType: "dreadnought", planet: "a", count: 2 },
      { baseType: "dreadnought", planet: "b", count: 1 },
    ]);
  });

  it("nie zabiera z celu bez przydziału", () => {
    const plan = { dreadnought: { a: 3 } };
    expect(shiftBombard(plan, dread, targets, "a", 1)).toBe(plan);
  });
});
