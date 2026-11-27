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
    seq: 9,
    is_current: true,
    created_at: null,
    activity: {
      kind: "tactical",
      action: "component.use",
      actor_id: "p1",
      target_id: null,
      subject: null,
      detail: null,
      round: 3,
      phase: "action",
      facts,
    },
  };
}

function tile(position: string, ships: string[] = []): Tile {
  return {
    position,
    systemId: "47",
    unitsByFaction: { yssaril: ships.map((entityId) => ({ entityId, entityType: "unit", count: 1 })) },
    planets: {},
    properties: { x: 0, y: 0 },
  } as unknown as Tile;
}

const isHero = (id: string) => id.endsWith("hero");

describe("Yssaril board effect (RULES.md 62.22)", () => {
  it("Kyver: every rival home system is an area of the hero's moment", () => {
    const moments = momentsForEntry(
      entry([
        fact({ type: "leader", player_id: "p1", value: "yssarilhero", detail: "purged" }),
        fact({ type: "area", player_id: "p1", value: "104", detail: "kyver" }),
        fact({ type: "area", player_id: "p1", value: "107", detail: "kyver" }),
      ]),
      isHero,
    );
    expect(moments).toHaveLength(1);
    const hero = moments[0];
    expect(hero.kind === "hero" && hero.leaderId).toBe("yssarilhero");
    expect(hero.kind === "hero" && hero.areas?.map((a) => `${a.position}:${a.kind}`)).toEqual([
      "104:kyver",
      "107:kyver",
    ]);
  });

  it("the recipe is the Yssaril's own keyhole in the mist, with flash, quake and sounds", () => {
    const recipe = HERO_BOARD_FX.yssarilhero;
    expect(recipe.mark).toBe("keyhole");
    expect(recipe.sweep).toBe("mist");
    expect(recipe.flashAt).toBeGreaterThan(0);
    expect(recipe.flashAt).toBeLessThan(recipe.ms);
    expect(recipe.quake?.[0].at).toBe(recipe.flashAt); // the blade's slash
    expect(recipe.sounds?.length).toBeGreaterThanOrEqual(5);
    expect(recipe.sounds?.every((s) => s.at < recipe.ms)).toBe(true);
  });

  it("targets the rival homes of the moment; without them falls back to the Yssaril's units", () => {
    const tiles = [tile("101", ["fs"]), tile("104"), tile("107")];
    const owner = {
      faction: "yssaril",
      color: null,
      areas: [
        { position: "104", self: true, kind: "kyver" as const },
        { position: "107", self: true, kind: "kyver" as const },
      ],
    };
    expect(fxTargets(HERO_BOARD_FX.yssarilhero, tiles, owner, null)).toEqual(["104", "107"]);
    expect(fxTargets(HERO_BOARD_FX.yssarilhero, tiles, { faction: "yssaril", color: null }, null)).toEqual([
      "101",
    ]);
  });
});
