import { describe, expect, it } from "vitest";
import type { PlayerData } from "@/entities/data/types";
import type { Tile } from "@/entities/game/types";
import { compareEmpires } from "./empireCompare";

const seat = (color: string, faction: string, over: Partial<PlayerData> = {}) =>
  ({
    discordId: color,
    color,
    faction,
    totalVps: 0,
    planets: [],
    exhaustedPlanets: [],
    techs: [],
    tg: 0,
    acCount: 0,
    tacticalCC: 3,
    fleetCC: 3,
    strategicCC: 2,
    totResources: 0,
    totInfluence: 0,
    ...over,
  }) as unknown as PlayerData;

const TILES = {
  "000": { position: "000", unitsByFaction: {}, planets: { jord: {}, mr: {} } },
  "101": { position: "101", unitsByFaction: {}, planets: { wellon: {} } },
} as unknown as Record<string, Tile>;

describe("compareEmpires", () => {
  const red = seat("red", "sol", { planets: ["jord"], techs: ["a", "b"], tg: 4 });
  const blue = seat("blue", "hacan", { planets: ["wellon", "mr"], techs: ["a", "b"], tg: 1 });
  const green = seat("green", "xxcha", { tg: 0 });
  const row = (id: string, shown = red) =>
    compareEmpires(shown, [red, blue, green], TILES).find((r) => r.id === id)!;

  it("ranks the shown player and names the leader", () => {
    expect(row("planets")).toMatchObject({ value: 1, rank: 2, players: 3, best: 2 });
    expect(row("planets").leaders.map((p) => p.color)).toEqual(["blue"]);
    expect(row("tg")).toMatchObject({ value: 4, rank: 1, total: 5, totalLabel: "at the table" });
  });

  it("shares a place on a tie and lists every leader", () => {
    expect(row("techs")).toMatchObject({ rank: 1, best: 2 });
    expect(row("techs").leaders).toHaveLength(2);
  });

  it("counts planets on the map as the total", () => {
    expect(row("planets")).toMatchObject({ total: 3, totalLabel: "on the map" });
  });

  it("has no leader while nobody has any", () => {
    expect(row("ac")).toMatchObject({ best: 0, leaders: [], rank: 1 });
  });

  it("does not sum a best-of measure", () => {
    expect(row("production").total).toBeNull();
  });
});
