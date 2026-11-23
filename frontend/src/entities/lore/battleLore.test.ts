import { describe, expect, it } from "vitest";
import { classifyBattle, describeBattle, type BattleLoreInput } from "./battleLore";

const base: BattleLoreInput = {
  kind: "space",
  where: "Mecatol Rex",
  attacker: "Federation of Sol",
  defender: "Hacan",
  winner: "attacker",
  rounds: 2,
  attackerLost: 0,
  defenderLost: 5,
  seed: 1,
};

describe("classifyBattle", () => {
  it("rozpoznaje rodzaje rozstrzygnięć", () => {
    expect(classifyBattle(base)).toBe("crushing");
    expect(classifyBattle({ ...base, attackerLost: 1, defenderLost: 1 })).toBe("skirmish");
    expect(classifyBattle({ ...base, attackerLost: 1, defenderLost: 4 })).toBe("decisive");
    expect(classifyBattle({ ...base, attackerLost: 3, defenderLost: 4, rounds: 4 })).toBe(
      "hard_fought",
    );
    expect(classifyBattle({ ...base, attackerLost: 4, defenderLost: 3 })).toBe("pyrrhic");
    expect(classifyBattle({ ...base, winner: null, attackerLost: 2, defenderLost: 3 })).toBe(
      "annihilation",
    );
    expect(classifyBattle({ ...base, winner: null, attackerLost: 0, defenderLost: 0 })).toBe(
      "standoff",
    );
  });
});

describe("describeBattle", () => {
  it("jest deterministyczny dla tego samego ziarna i podstawia nazwy", () => {
    const a = describeBattle(base);
    expect(describeBattle(base)).toEqual(a);
    expect(a.cls).toBe("crushing");
    expect(a.text).not.toMatch(/\{\w+\}/);
    expect(a.text.length).toBeGreaterThan(20);
  });

  it("opisuje typy strat pełnymi nazwami", () => {
    const text = describeBattle({
      ...base,
      defenderTypes: { dreadnought: 2, carrier: 1 },
      typeName: (b) => (b === "dreadnought" ? "Dreadnought" : "Carrier"),
    });
    // niezależnie od wylosowanego wariantu nie zostaje żaden znacznik
    expect(text.text).not.toMatch(/\{\w+\}/);
  });

  it("każdy wariant każdej klasy daje kompletny tekst", () => {
    for (let seed = 0; seed < 40; seed++) {
      for (const kind of ["space", "ground"] as const) {
        for (const winner of ["attacker", "defender", null] as const) {
          for (const [aLost, dLost, rounds] of [
            [0, 6, 1],
            [1, 4, 2],
            [3, 4, 4],
            [5, 3, 3],
            [1, 1, 1],
            [3, 3, 2],
            [0, 0, 1],
          ] as const) {
            const out = describeBattle({
              ...base,
              kind,
              winner,
              attackerLost: aLost,
              defenderLost: dLost,
              rounds,
              seed,
            });
            expect(out.text).not.toMatch(/\{\w*\}|undefined|NaN/);
          }
        }
      }
    }
  });
});
