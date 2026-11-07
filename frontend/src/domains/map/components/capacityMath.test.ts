import { describe, expect, it } from "vitest";
import type { CapacityView } from "@/api/useBoardEditor";
import { excessFor, removalStatus, remainingCargo } from "./capacityMath";

function view(partial: Partial<CapacityView>): CapacityView {
  return {
    active: true,
    position: "000",
    player: "red",
    playerId: "p1",
    general: 0,
    fighterOnly: 0,
    used: 0,
    excess: 0,
    cargo: [],
    suggestion: {},
    remaining: 1,
    ...partial,
  };
}

const cargo = [
  { baseType: "fighter", asyncId: "ff", name: "Fighter", count: 4, cost: 1 },
  { baseType: "infantry", asyncId: "gf", name: "Infantry", count: 2, cost: 1 },
];

describe("capacityMath", () => {
  it("counts excess over ship capacity", () => {
    const v = view({ general: 4, cargo });
    expect(excessFor(v, remainingCargo(v, {}))).toBe(2);
  });

  it("parks fighters on the dock allocation first", () => {
    const v = view({ general: 2, fighterOnly: 3, cargo });
    // 3 myśliwce na doku, 1 myśliwiec + 2 piechoty na 2 miejscach statków → 1 za dużo.
    expect(excessFor(v, remainingCargo(v, {}))).toBe(1);
  });

  it("reports over / exact / tooMany", () => {
    const v = view({ general: 4, cargo });
    expect(removalStatus(v, { fighter: 1 })).toBe("over");
    expect(removalStatus(v, { fighter: 1, infantry: 1 })).toBe("exact");
    expect(removalStatus(v, { fighter: 3 })).toBe("tooMany");
  });
});
