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
    unitsByFaction: { mahact: ships.map((entityId) => ({ entityId, entityType: "unit", count: 1 })) },
    planets: {},
    properties: { x: 0, y: 0 },
  } as unknown as Tile;
}

const isHero = (id: string) => id.endsWith("hero");

describe("Mahact board effect (RULES.md 62.23)", () => {
  it("Benediction: the origin and the combat system are areas of the hero's moment", () => {
    const moments = momentsForEntry(
      entry([
        fact({ type: "leader", player_id: "p1", value: "mahacthero", detail: "purged" }),
        fact({ type: "area", player_id: "p1", value: "102", detail: "benediction_origin" }),
        fact({ type: "area", player_id: "p1", value: "103", detail: "benediction" }),
      ]),
      isHero,
    );
    expect(moments).toHaveLength(1);
    const hero = moments[0];
    expect(hero.kind === "hero" && hero.leaderId).toBe("mahacthero");
    expect(hero.kind === "hero" && hero.areas?.map((a) => `${a.position}:${a.kind}`)).toEqual([
      "102:benediction_origin",
      "103:benediction",
    ]);
  });

  it("the recipe is the Mahact's own binding chain, with flash, quake and sounds", () => {
    const recipe = HERO_BOARD_FX.mahacthero;
    expect(recipe.mark).toBe("benediction");
    expect(recipe.flashAt).toBeGreaterThan(0);
    expect(recipe.flashAt).toBeLessThan(recipe.ms);
    expect(recipe.quake?.[0].at).toBe(recipe.flashAt); // the links slam shut
    expect(recipe.sounds?.length).toBeGreaterThanOrEqual(5);
    expect(recipe.sounds?.every((s) => s.at < recipe.ms)).toBe(true);
  });

  it("targets the two systems of the moment; without them falls back to the Mahact's ships", () => {
    const tiles = [tile("101", ["fs"]), tile("102"), tile("103")];
    const owner = {
      faction: "mahact",
      color: null,
      areas: [
        { position: "102", self: true, kind: "benediction_origin" as const },
        { position: "103", self: true, kind: "benediction" as const },
      ],
    };
    expect(fxTargets(HERO_BOARD_FX.mahacthero, tiles, owner, null)).toEqual(["102", "103"]);
    expect(fxTargets(HERO_BOARD_FX.mahacthero, tiles, { faction: "mahact", color: null }, null)).toEqual([
      "101",
    ]);
  });
});
