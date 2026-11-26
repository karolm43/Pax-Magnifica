import { describe, expect, it } from "vitest";
import type { ActivityEntry, ActivityFact } from "@/api/useBoardEditor";
import type { Tile } from "@/entities/game/types";
import { HERO_BOARD_FX, TETHER_BOARD_FX, fxTargets } from "./heroBoardFx";
import { momentsForEntry, tetherBorder } from "./keyMoments";

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
    unitsByFaction: { empyrean: ships.map((entityId) => ({ entityId, entityType: "unit", count: 1 })) },
    planets: {},
    properties: { x: 0, y: 0 },
  } as unknown as Tile;
}

const isHero = (id: string) => id.endsWith("hero");

describe("Empyrean board effects (RULES.md 62.20)", () => {
  it("Multiverse Shift: placed and explored frontier systems are the hero's areas", () => {
    const moments = momentsForEntry(
      entry([
        fact({ type: "leader", player_id: "p1", value: "empyreanhero", detail: "purged" }),
        fact({ type: "area", player_id: "p1", value: "201", detail: "frontier" }),
        fact({ type: "area", player_id: "p1", value: "202", detail: "frontier" }),
        fact({ type: "area", player_id: "p1", value: "203", detail: "explore" }),
      ]),
      isHero,
    );
    expect(moments).toHaveLength(1);
    const hero = moments[0];
    expect(hero.kind === "hero" && hero.areas?.map((a) => `${a.position}:${a.kind}`)).toEqual([
      "201:frontier",
      "202:frontier",
      "203:explore",
    ]);
  });

  it("Multiverse Shift recipe: a void eye over every touched system, flash + sounds", () => {
    const recipe = HERO_BOARD_FX.empyreanhero;
    expect(recipe.mark).toBe("voideye");
    const board = [tile("201"), tile("202"), tile("203"), tile("204", ["dd"])];
    const owner = {
      faction: "empyrean",
      color: "purple",
      areas: [
        { position: "201", self: true, kind: "frontier" as const },
        { position: "203", self: true, kind: "explore" as const },
      ],
    };
    expect(fxTargets(recipe, board, owner, null)).toEqual(["201", "203"]);
    // No areas (nothing placed): the Empyrean ships' systems instead of an empty board.
    expect(fxTargets(recipe, board, { faction: "empyrean", color: "purple" }, null)).toEqual(["204"]);
    expect(recipe.flashAt).toBeLessThan(recipe.ms);
    expect(recipe.sounds?.length).toBeGreaterThan(3);
  });

  it("Void Tether: a border token fact = tether moment (both systems, the old border)", () => {
    expect(tetherBorder({ value: "voidtether", detail: "border:105", position: "104" })).toEqual(["104", "105"]);
    expect(tetherBorder({ value: "sleeper", detail: "border:105", position: "104" })).toBeNull();
    expect(tetherBorder({ value: "voidtether", detail: "space", position: "104" })).toBeNull();
    const placed = momentsForEntry(
      entry([fact({ type: "faction_token", player_id: "p1", value: "voidtether", detail: "border:105", position: "104" })]),
      isHero,
    );
    expect(placed).toEqual([{ kind: "tether", seq: 9, player: "p1", a: "104", b: "105", from: null }]);
    const moved = momentsForEntry(
      entry([
        fact({ type: "faction_token", player_id: "p1", value: "voidtether", detail: "border:202", position: "101" }),
        fact({ type: "faction_token_removed", player_id: "p1", value: "voidtether", detail: "border:105", position: "104" }),
      ]),
      isHero,
    );
    expect(moved).toEqual([{ kind: "tether", seq: 9, player: "p1", a: "101", b: "202", from: ["104", "105"] }]);
    // Removed only (no new border): nothing seals - no moment.
    const removed = momentsForEntry(
      entry([fact({ type: "faction_token_removed", player_id: "p1", value: "voidtether", detail: "border:105", position: "104" })]),
      isHero,
    );
    expect(removed).toEqual([]);
  });

  it("Void Tether recipe targets both systems of the border", () => {
    const board = [tile("104"), tile("105"), tile("106")];
    const owner = {
      faction: "empyrean",
      color: "purple",
      areas: [
        { position: "104", self: true, kind: "gain" as const },
        { position: "105", self: true, kind: "gain" as const },
        { position: "106", self: true, kind: "loss" as const },
      ],
    };
    expect(TETHER_BOARD_FX.mark).toBe("tether");
    expect(fxTargets(TETHER_BOARD_FX, board, owner, null)).toEqual(["104", "105"]);
  });
});
