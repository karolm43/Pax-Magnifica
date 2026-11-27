import { describe, expect, it } from "vitest";
import type { ActivityEntry, ActivityFact } from "@/api/useBoardEditor";
import type { Tile } from "@/entities/game/types";
import { HERO_BOARD_FX, fxTargets } from "./heroBoardFx";
import { momentsForEntry } from "./keyMoments";

const fact = (f: Partial<ActivityFact> & { type: string }): ActivityFact => ({
  player_id: null,
  value: null,
  delta: null,
  detail: null,
  ...f,
});

function entry(facts: ActivityFact[]): ActivityEntry {
  return {
    seq: 4,
    is_current: true,
    created_at: null,
    activity: {
      kind: "tactical",
      action: "component.use",
      actor_id: "p1",
      target_id: null,
      subject: null,
      detail: null,
      round: 2,
      phase: "action",
      facts,
    },
  };
}

function tile(position: string, ships: string[] = []): Tile {
  return {
    position,
    systemId: "47",
    unitsByFaction: { nomad: ships.map((entityId) => ({ entityId, entityType: "unit", count: 1 })) },
    planets: {},
    properties: { x: 0, y: 0 },
  } as unknown as Tile;
}

const isHero = (id: string) => id.endsWith("hero");

describe("Nomad board effect (RULES.md 62.21)", () => {
  it("Time Warp: the flagship's system and the command-token systems are the hero's areas", () => {
    const moments = momentsForEntry(
      entry([
        fact({ type: "leader", player_id: "p1", value: "nomadhero", detail: "purged" }),
        fact({ type: "area", player_id: "p1", value: "101", detail: "time_warp" }),
        fact({ type: "area", player_id: "p1", value: "104", detail: "time_warp_token" }),
      ]),
      isHero,
    );
    expect(moments).toHaveLength(1);
    const hero = moments[0];
    expect(hero.kind === "hero" && hero.leaderId).toBe("nomadhero");
    expect(hero.kind === "hero" && hero.areas?.map((a) => `${a.position}:${a.kind}`)).toEqual([
      "101:time_warp",
      "104:time_warp_token",
    ]);
  });

  it("the recipe is the Nomad's own chronometer, not a generic ring, with flash and sounds", () => {
    const recipe = HERO_BOARD_FX.nomadhero;
    expect(recipe.mark).toBe("timewarp");
    expect(recipe.flashAt).toBeGreaterThan(0);
    expect(recipe.flashAt).toBeLessThan(recipe.ms);
    expect(recipe.sounds?.some((s) => s.reverse)).toBe(true); // time running back
    expect(recipe.sounds?.every((s) => s.at < recipe.ms)).toBe(true);
  });

  it("targets the moment's areas; without them falls back to the flagship's ships", () => {
    const tiles = [tile("101", ["fs"]), tile("104"), tile("105")];
    const owner = {
      faction: "nomad",
      color: null,
      areas: [
        { position: "101", self: true, kind: "time_warp" as const },
        { position: "104", self: true, kind: "time_warp_token" as const },
      ],
    };
    expect(fxTargets(HERO_BOARD_FX.nomadhero, tiles, owner, null)).toEqual(["101", "104"]);
    expect(fxTargets(HERO_BOARD_FX.nomadhero, tiles, { faction: "nomad", color: null }, null)).toEqual([
      "101",
    ]);
  });
});
