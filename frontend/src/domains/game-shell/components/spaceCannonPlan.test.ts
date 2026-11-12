import { describe, expect, it } from "vitest";
import { spaceCannonPlan } from "./SpaceCannonParts";

const dread = {
  baseType: "dreadnought",
  asyncId: "dn",
  name: "Dreadnought",
  count: 2,
  damaged: 0,
  sustain: true,
};

describe("spaceCannonPlan (Sustain Damage przeciw Space Cannon)", () => {
  it("sam Sustain Damage nie niszczy statku", () => {
    expect(spaceCannonPlan([dread], { dreadnought: 1 }, {})).toEqual({
      sustain: [{ baseType: "dreadnought", count: 1 }],
      destroy: [],
      destroyDamaged: [],
    });
  });

  it("zniszczenie idzie najpierw w statek właśnie uszkodzony", () => {
    expect(
      spaceCannonPlan([dread], { dreadnought: 1 }, { dreadnought: 2 }),
    ).toEqual({
      sustain: [{ baseType: "dreadnought", count: 1 }],
      destroy: [{ baseType: "dreadnought", count: 1 }],
      destroyDamaged: [{ baseType: "dreadnought", count: 1 }],
    });
  });

  it("statek bez Sustain Damage po prostu ginie", () => {
    const destroyer = {
      baseType: "destroyer",
      asyncId: "dd",
      name: "Destroyer",
      count: 1,
    };
    expect(spaceCannonPlan([destroyer], {}, { destroyer: 1 }).destroy).toEqual([
      { baseType: "destroyer", count: 1 },
    ]);
  });
});
