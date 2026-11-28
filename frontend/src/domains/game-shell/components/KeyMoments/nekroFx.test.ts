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
    seq: 11,
    is_current: true,
    created_at: null,
    activity: {
      kind: "tactical",
      action: "component.use",
      actor_id: "p1",
      target_id: null,
      subject: null,
      detail: null,
      round: 4,
      phase: "action",
      facts,
    },
  };
}

function tile(position: string, ships: string[] = []): Tile {
  return {
    position,
    systemId: "19",
    unitsByFaction: { nekro: ships.map((entityId) => ({ entityId, entityType: "unit", count: 1 })) },
    planets: {},
    properties: { x: 0, y: 0 },
  } as unknown as Tile;
}

const isHero = (id: string) => id.endsWith("hero");

describe("Nekro board effect (RULES.md 62.24)", () => {
  it("Devour World: the system is the hero's area and the devoured planet its planet", () => {
    const moments = momentsForEntry(
      entry([
        fact({ type: "leader", player_id: "p1", value: "nekrohero", detail: "purged" }),
        fact({ type: "area", player_id: "p1", value: "105", detail: "nekro_devour" }),
        fact({ type: "hero_planet", player_id: "p1", value: "wellon" }),
      ]),
      isHero,
    );
    expect(moments).toHaveLength(1);
    const hero = moments[0];
    expect(hero.kind === "hero" && hero.leaderId).toBe("nekrohero");
    expect(hero.kind === "hero" && hero.areas?.map((a) => a.position + ":" + a.kind)).toEqual([
      "105:nekro_devour",
    ]);
    expect(hero.kind === "hero" && hero.planets).toEqual(["wellon"]);
  });

  it("the recipe is the Nekro's own viral devour, with static, flash, quake and sounds", () => {
    const recipe = HERO_BOARD_FX.nekrohero;
    expect(recipe.mark).toBe("devour");
    expect(recipe.sweep).toBe("static");
    expect(recipe.flashAt).toBeGreaterThan(0);
    expect(recipe.flashAt).toBeLessThan(recipe.ms);
    expect(recipe.quake?.[0].at).toBe(recipe.flashAt); // the implosion
    expect(recipe.sounds?.length).toBeGreaterThanOrEqual(5);
    expect(recipe.sounds?.every((s) => s.at < recipe.ms)).toBe(true);
  });

  it("targets the devoured system; without it falls back to the Nekro's units", () => {
    const tiles = [tile("101", ["fs"]), tile("105")];
    const owner = {
      faction: "nekro",
      color: null,
      areas: [{ position: "105", self: true, kind: "nekro_devour" as const }],
    };
    expect(fxTargets(HERO_BOARD_FX.nekrohero, tiles, owner, null)).toEqual(["105"]);
    expect(fxTargets(HERO_BOARD_FX.nekrohero, tiles, { faction: "nekro", color: null }, null)).toEqual([
      "101",
    ]);
  });
});
