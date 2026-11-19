import { describe, expect, it } from "vitest";
import type { ShipEntity } from "./battleAssign";
import type { ShipView } from "./useBattleFx";
import { wingRank } from "./BattleFleet";

const fighters = (n: number): ShipView[] =>
  Array.from({ length: n }, (_, i) => ({
    ship: {
      id: `fighter-${i}`,
      baseType: "fighter",
      asyncId: "ff",
      name: "Fighter",
      damaged: false,
      canSustain: false,
      unit: {} as ShipEntity["unit"],
    },
    dying: false,
    dieDelay: 0,
    leaving: false,
    justSustained: false,
  }));

/*
 * Szereg myśliwców liczony płasko (bez pudełek eskadr): przegrupowanie eskadr po stratach
 * z AFB nie może przemontowywać okrętów — każdy myśliwiec ma pozycję w jednym pudełku szeregu.
 */
describe("wingRank — płaski szereg myśliwców", () => {
  it("każdy myśliwiec ma pozycję w obrębie pudełka szeregu", () => {
    const list = fighters(7);
    const wing = wingRank(list, 1, "left");
    expect(wing.places.size).toBe(7);
    for (const p of wing.places.values()) {
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThan(wing.width);
      expect(p.y).toBeLessThan(wing.height);
    }
  });

  it("eskadry równej liczebności (7 → 4 + 3), druga kolumna przy >2 eskadrach", () => {
    const seven = wingRank(fighters(7), 1, "left");
    const sq = [...seven.places.values()].map((p) => p.sq);
    expect(sq.filter((s) => s === 0)).toHaveLength(4);
    expect(sq.filter((s) => s === 1)).toHaveLength(3);
    const many = wingRank(fighters(12), 1, "right");
    expect(new Set([...many.places.values()].map((p) => p.sq)).size).toBe(3);
    expect(many.width).toBeGreaterThan(seven.width);
  });

  it("pozycje są różne (myśliwce nie nakładają się)", () => {
    const wing = wingRank(fighters(10), 0.8, "right");
    const keys = new Set([...wing.places.values()].map((p) => `${p.x}:${p.y}`));
    expect(keys.size).toBe(10);
  });
});
