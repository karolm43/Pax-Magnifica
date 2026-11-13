/*
 * Testy logiki przypisania strat w oknie pola bitwy (RULES.md 39 W7/W8).
 *
 * Plan wysyłany do silnika musi odzwierciedlać znaczniki egzemplarzy: Sustain Damage
 * uszkadza, „oba" = Sustain + zniszczenie tego samego okrętu (przyjmuje 2 trafienia),
 * a zniszczenie uszkodzonego idzie osobnym kubełkiem (destroyDamaged).
 */

import { describe, it, expect } from "vitest";
import type { BattleSide, BattleUnit } from "@/api/useBoardEditor";
import {
  absorbed,
  autoMarks,
  coveredCount,
  expandShips,
  isCovered,
  nextMark,
  planFromMarks,
  toggleMark,
} from "./battleAssign";

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

function side(units: BattleUnit[]): BattleSide {
  return {
    faction: "p2",
    playerId: "p2",
    role: "defender",
    units,
    unitCount: units.reduce((n, u) => n + u.count, 0),
    totalDice: 0,
    expectedHits: 0,
    hp: 0,
  };
}

const dreadnoughts = unit({
  baseType: "dreadnought",
  asyncId: "dn",
  name: "Dreadnought",
  count: 2,
  damaged: 1,
  hitsOn: 5,
  baseHitsOn: 5,
  sustain: true,
  sustainable: 1,
});
const fighters = unit({
  baseType: "fighter",
  asyncId: "ff",
  name: "Fighter",
  count: 2,
  hitsOn: 9,
  baseHitsOn: 9,
});

describe("expandShips", () => {
  it("rozwija stosy w egzemplarze, pierwsze `damaged` są uszkodzone", () => {
    const ships = expandShips(side([dreadnoughts]));
    expect(ships.map((s) => [s.id, s.damaged, s.canSustain])).toEqual([
      ["dreadnought-0", true, false],
      ["dreadnought-1", false, true],
    ]);
  });
});

describe("nextMark", () => {
  it("statek z gotowym Sustain: sustain → destroy → oba → brak", () => {
    const [, ready] = expandShips(side([dreadnoughts]));
    expect(nextMark(ready, undefined)).toBe("sustain");
    expect(nextMark(ready, "sustain")).toBe("destroy");
    expect(nextMark(ready, "destroy")).toBe("both");
    expect(nextMark(ready, "both")).toBeUndefined();
  });

  it("zwykły / uszkodzony statek: tylko zniszczenie", () => {
    const [damaged] = expandShips(side([dreadnoughts]));
    expect(nextMark(damaged, undefined)).toBe("destroy");
    expect(nextMark(damaged, "destroy")).toBeUndefined();
  });
});

describe("planFromMarks", () => {
  it("rozdziela sustain, destroy i destroyDamaged zgodnie z semantyką silnika", () => {
    const ships = expandShips(side([dreadnoughts, fighters]));
    const plan = planFromMarks(ships, {
      "dreadnought-0": "destroy", // uszkodzony → destroyDamaged
      "dreadnought-1": "both", // sustain + zniszczenie tego samego → sustain + destroyDamaged
      "fighter-0": "destroy", // nieuszkodzony → destroy
    });
    expect(plan).toEqual({
      sustain: { dreadnought: 1 },
      destroy: { fighter: 1 },
      destroyDamaged: { dreadnought: 2 },
    });
    expect(
      absorbed({
        "dreadnought-0": "destroy",
        "dreadnought-1": "both",
        "fighter-0": "destroy",
      }),
    ).toBe(4);
  });
});

describe("autoMarks", () => {
  it("najpierw Sustain Damage, potem najsłabsze jednostki", () => {
    const ships = expandShips(side([dreadnoughts, fighters]));
    const marks = autoMarks(ships, 2);
    expect(marks).toEqual({
      "dreadnought-1": "sustain",
      "fighter-0": "destroy",
    });
    expect(absorbed(marks)).toBe(2);
  });

  it("gdy trafień więcej niż jednostek, dobija egzemplarze po Sustain", () => {
    const ships = expandShips(side([dreadnoughts, fighters]));
    // 4 jednostki + 1 Sustain = maksymalnie 5 trafień.
    const marks = autoMarks(ships, 5);
    expect(absorbed(marks)).toBe(5);
    expect(marks["dreadnought-1"]).toBe("both");
    expect(Object.keys(marks)).toHaveLength(4);
  });
});

describe("Non-Euclidean Shielding (Sustain anuluje 2 trafienia)", () => {
  // Scenariusz z gry: Letnev 9 statków, 2 z gotowym Sustain → 9 + 2×2 = 13 trafień do pokrycia.
  const letnev = side([
    unit({ baseType: "dreadnought", asyncId: "dn", count: 1, sustain: true, sustainable: 1 }),
    unit({ baseType: "flagship", asyncId: "fs", count: 1, sustain: true, sustainable: 1 }),
    unit({ baseType: "fighter", asyncId: "ff", count: 5, hitsOn: 9, baseHitsOn: 9 }),
    unit({ baseType: "cruiser", asyncId: "ca", count: 1 }),
    unit({ baseType: "destroyer", asyncId: "dd", count: 1 }),
  ]);

  it("Auto pokrywa 13 trafień (tarcze ×2 + wszystkie jednostki)", () => {
    const ships = expandShips(letnev);
    const marks = autoMarks(ships, 13, 2);
    expect(absorbed(marks, 2)).toBe(13);
    expect(isCovered(marks, 13, 2)).toBe(true);
    expect(marks["dreadnought-0"]).toBe("both");
  });

  it("klikanie dochodzi do 13 i nie przekracza wymaganych", () => {
    const ships = expandShips(letnev);
    let marks = {};
    for (const ship of ships) {
      marks = toggleMark(marks, ship, 13, 2); // tarcza (2) albo zniszczenie (1)
    }
    expect(absorbed(marks, 2)).toBe(11);
    marks = toggleMark(marks, ships[0], 13, 2); // sustain → destroy (1): 10
    marks = toggleMark(marks, ships[0], 13, 2); // destroy → oba (3): 12
    expect(absorbed(marks, 2)).toBe(12);
    marks = toggleMark(marks, ships[1], 13, 2); // fs: sustain → destroy: 11
    marks = toggleMark(marks, ships[1], 13, 2); // fs: oba: 13
    expect(isCovered(marks, 13, 2)).toBe(true);
  });

  it("ostatnia tarcza może anulować mniej (1 trafienie, tylko tarcze)", () => {
    const ships = expandShips(letnev);
    const marks = toggleMark({}, ships[0], 1, 2);
    expect(marks).toEqual({ "dreadnought-0": "sustain" });
    expect(isCovered(marks, 1, 2)).toBe(true);
    expect(coveredCount(marks, 1, 2)).toBe(1);
  });
});
