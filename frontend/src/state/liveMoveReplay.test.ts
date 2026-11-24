import { describe, expect, it } from "vitest";
import type { ActivityEntry, ActivityFact } from "@/api/boardQueries";
import type { GameData } from "@/entities/game/types";
import type { EntityStack } from "@/entities/positioning";
import {
  liveMoveFromEntry,
  moveLanded,
  replayBaseline,
} from "./liveMoveReplay";

/** Cruisers of Sol in space, per system position. */
function data(units: Record<string, number>): GameData {
  return {
    tiles: Object.fromEntries(
      Object.entries(units).map(([position, count]) => [
        position,
        {
          properties: { x: 0, y: 0 },
          entityPlacements:
            count > 0
              ? [
                  {
                    entityType: "unit",
                    entityId: "ca",
                    faction: "sol",
                    count,
                    x: 0,
                    y: 0,
                  } as EntityStack,
                ]
              : [],
        },
      ]),
    ),
  } as unknown as GameData;
}

function entry(facts: ActivityFact[], action = "tactical.move"): ActivityEntry {
  return {
    seq: 5,
    is_current: true,
    created_at: null,
    activity: {
      kind: "tactical",
      action,
      actor_id: "p1",
      target_id: null,
      subject: "202",
      detail: null,
      round: 1,
      phase: "action",
      facts,
    },
  };
}

const players = {
  p1: { faction: "sol", color: "blue", display_name: "P1", is_bot: false },
};
const routeFact: ActivityFact = {
  type: "move_route",
  player_id: "p1",
  value: null,
  delta: null,
  detail: null,
  route: ["202", "101", "000"],
  hops: ["lane", "wormhole"],
  anomalies: { "000": ["NEBULA"] },
};

describe("liveMoveFromEntry", () => {
  it("reads the route of a tactical move", () => {
    expect(liveMoveFromEntry(entry([routeFact]), players)).toEqual({
      faction: "sol",
      route: ["202", "101", "000"],
      hops: ["lane", "wormhole"],
      anomalies: { "000": ["NEBULA"] },
    });
  });

  it("ignores entries without a route and other actions", () => {
    expect(liveMoveFromEntry(entry([]), players)).toBeUndefined();
    expect(
      liveMoveFromEntry(entry([routeFact], "tactical.produce"), players),
    ).toBeUndefined();
  });
});

describe("pairing a move with the live map", () => {
  const move = {
    faction: "sol",
    route: ["202", "101", "000"],
    hops: [],
    anomalies: {},
  };
  const before = data({ "202": 2, "000": 0 });
  const after = data({ "202": 0, "000": 2 });
  const unrelated = data({ "202": 2, "000": 0, "101": 0 });

  it("recognises the move only when units left the source and reached the target", () => {
    expect(moveLanded(before, after, move)).toBe(true);
    expect(moveLanded(before, unrelated, move)).toBe(false);
  });

  it("uses the map from when the entry arrived if the map refreshed later", () => {
    expect(
      replayBaseline(
        { move, liveAtArrival: before, previousAtArrival: undefined },
        after,
      ),
    ).toBe(before);
  });

  it("uses the map before the last refresh if that refresh came first", () => {
    expect(
      replayBaseline(
        { move, liveAtArrival: after, previousAtArrival: before },
        after,
      ),
    ).toBe(before);
  });

  it("keeps waiting while the map has not shown the move", () => {
    expect(
      replayBaseline(
        { move, liveAtArrival: before, previousAtArrival: undefined },
        before,
      ),
    ).toBeUndefined();
  });
});
