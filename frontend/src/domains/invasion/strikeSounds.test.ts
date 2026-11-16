import { describe, expect, it } from "vitest";
import { strikeSounds } from "./InvasionFx";
import type { InvasionLogEntry } from "./useInvasion";

function entry(
  phase: InvasionLogEntry["phase"],
  baseType: string,
  dice: number[],
): InvasionLogEntry {
  return {
    phase,
    planet: "p",
    defender: null,
    rolls: [{ baseType, name: baseType, count: dice.length, hitsOn: 5, dice, hits: 0 }],
    hits: 0,
    losses: {},
    sustained: {},
  };
}

describe("dźwięki salwy inwazji", () => {
  it("bombardowanie: wystrzał, wybuch na ziemi przy trafieniu, cichy flak przy pudle", () => {
    const plan = strikeSounds(entry("BOMBARDMENT", "dreadnought", [9, 2]), "orbit", 100);
    expect(plan.filter((s) => s.name === "plasma")).toHaveLength(2);
    expect(plan.filter((s) => s.name === "groundBlast")).toHaveLength(1);
    expect(plan.filter((s) => s.name === "flak")).toHaveLength(1);
    expect(plan[0].ms).toBe(100);
    expect(plan.map((s) => s.ms)).toEqual([...plan.map((s) => s.ms)].sort((a, b) => a - b));
  });

  it("war sun strzela lancą (sunfire) i trafia ciężkim wybuchem", () => {
    const plan = strikeSounds(entry("BOMBARDMENT", "warsun", [10]), "orbit", 0);
    expect(plan.map((s) => s.name)).toEqual(["sunfire", "groundBlast"]);
    expect(plan[1].heavy).toBe(true);
  });

  it("Space Cannon Defense: wybuch tylko zestrzelonej kapsuły", () => {
    const plan = strikeSounds(entry("DEFENSE", "pds", [6, 1]), "ground", 0);
    expect(plan.filter((s) => s.name === "explosion")).toHaveLength(1);
  });

  it("duża salwa ma limit dźwięków", () => {
    const plan = strikeSounds(entry("BOMBARDMENT", "dreadnought", Array.from({ length: 20 }, () => 9)), "orbit", 0);
    expect(plan.length).toBeLessThanOrEqual(14);
  });
});
