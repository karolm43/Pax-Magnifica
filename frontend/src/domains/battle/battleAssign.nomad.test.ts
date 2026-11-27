/*
 * Hit shields in the assignment (Quantum Manipulator, RULES.md 62.21): a Nomad mech in the space
 * area may only cancel a hit with Sustain Damage - never be destroyed by it.
 */
import { describe, expect, it } from "vitest";
import type { BattleSide, BattleUnit } from "@/api/useBoardEditor";
import { assignableShips, autoMarks, expandShips, nextMark, planFromMarks } from "./battleAssign";

function unit(overrides: Partial<BattleUnit>): BattleUnit {
  return {
    baseType: "cruiser",
    asyncId: "ca",
    name: "Cruiser",
    count: 1,
    damaged: 0,
    hitsOn: 7,
    baseHitsOn: 7,
    modifier: 0,
    dicePerUnit: 1,
    totalDice: 1,
    expectedHits: 0.4,
    sustain: false,
    sustainable: 0,
    afbHitsOn: null,
    afbDice: 1,
    ...overrides,
  };
}

const mech = unit({
  baseType: "mech", asyncId: "mf", name: "Quantum Manipulator", hitsOn: 11, baseHitsOn: 11,
  dicePerUnit: 0, totalDice: 0, sustain: true, sustainable: 1, shield: true,
});

function side(units: BattleUnit[]): BattleSide {
  return {
    faction: "nomad", playerId: "p1", role: "defender", units,
    unitCount: 1, totalDice: 1, expectedHits: 0.4, hp: 2,
  };
}

describe("Quantum Manipulator hit shield (RULES.md 62.21)", () => {
  it("a shield only takes the Sustain Damage mark", () => {
    const [cruiser, shield] = expandShips(side([unit({}), mech]));
    expect(shield.shield).toBe(true);
    expect(nextMark(shield, undefined)).toBe("sustain");
    expect(nextMark(shield, "sustain")).toBeUndefined();
    expect(nextMark(cruiser, undefined)).toBe("destroy");
  });

  it("Auto cancels with the shield first and never destroys it", () => {
    const ships = expandShips(side([unit({}), mech]));
    const plan = planFromMarks(ships, autoMarks(ships, 2));
    expect(plan.sustain).toEqual({ mech: 1 });
    expect(plan.destroy).toEqual({ cruiser: 1 });
  });

  it("directed hits (AFB on fighters) may still be cancelled by the shield", () => {
    const ships = expandShips(side([unit({ baseType: "fighter", asyncId: "ff", name: "Fighter" }), mech]));
    const allowed = assignableShips(ships, { types: ["fighter"], count: 1, label: "AFB", damaged: null, chooser: "" }, 1);
    expect(allowed.map((s) => s.baseType)).toEqual(["fighter", "mech"]);
  });
});
