import { autoAssignHits } from "./SpaceCannonParts";
import type { SpaceCannonShip } from "@/api/useBoardEditor";

const COST: Record<string, number> = { fighter: 0.5, destroyer: 1, cruiser: 2, dreadnought: 4 };
const costOf = (ship: SpaceCannonShip) => COST[ship.baseType] ?? 0;
const ship = (baseType: string, count: number, over: Partial<SpaceCannonShip> = {}) => ({
  baseType,
  asyncId: baseType,
  name: baseType,
  count,
  ...over,
});

describe("Auto hit assignment (RULES.md 38.4)", () => {
  it("uses Sustain Damage first, then destroys the cheapest ships", () => {
    const plan = autoAssignHits(
      [ship("dreadnought", 1, { sustain: true }), ship("cruiser", 1), ship("fighter", 2)],
      3,
      1,
      costOf,
    );
    expect(plan).toEqual({ sustain: { dreadnought: 1 }, destroyed: { fighter: 2 } });
  });

  it("a damaged ship has no Sustain Damage left", () => {
    const plan = autoAssignHits(
      [ship("dreadnought", 1, { sustain: true, damaged: 1 }), ship("destroyer", 1)],
      1,
      1,
      costOf,
    );
    expect(plan).toEqual({ sustain: {}, destroyed: { destroyer: 1 } });
  });

  it("a shield cancelling 2 hits covers both", () => {
    const plan = autoAssignHits([ship("dreadnought", 1, { sustain: true })], 2, 2, costOf);
    expect(plan).toEqual({ sustain: { dreadnought: 1 }, destroyed: {} });
  });
});
