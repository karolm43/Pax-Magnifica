import { describe, expect, it } from "vitest";
import type { ActivityEntry, ActivityFact } from "@/api/boardQueries";
import type { GameData } from "@/entities/game/types";
import type { EntityStack } from "@/entities/positioning";
import type { LiveMove } from "@/entities/replay/types";
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
      kind: "move",
      faction: "sol",
      route: ["202", "101", "000"],
      hops: ["lane", "wormhole"],
      anomalies: { "000": ["NEBULA"] },
    });
  });

  it("reads the planets of an invasion landing", () => {
    const landed = (planet: string): ActivityFact => ({
      type: "landed",
      player_id: "p1",
      value: "infantry",
      delta: 2,
      detail: planet,
    });
    expect(
      liveMoveFromEntry(
        entry([landed("lodor"), landed("lodor")], "invasion.commit"),
        players,
      ),
    ).toEqual({ kind: "landing", faction: "sol", planets: ["lodor"] });
  });

  it("reads ships and cargo a gravity rift swallowed, as map unit ids", () => {
    const lost = (value: string, delta: number): ActivityFact => ({
      type: "rift_lost",
      player_id: "p1",
      value,
      delta,
      detail: "101",
    });
    const move = liveMoveFromEntry(
      entry([routeFact, lost("cruiser", 1), lost("fighter", 2)]),
      players,
    );
    expect(move).toMatchObject({
      kind: "move",
      lost: [
        { unitId: "ca", count: 1, at: "101" },
        { unitId: "ff", count: 2, at: "101" },
      ],
    });
  });

  it("reads the ships that spent Gravity Drive, as map unit ids", () => {
    const drive: ActivityFact = {
      type: "gravity_drive",
      player_id: "p1",
      value: "cruiser",
      delta: null,
      detail: null,
    };
    expect(liveMoveFromEntry(entry([routeFact, drive]), players)).toMatchObject({
      kind: "move",
      boosted: ["ca"],
    });
    expect(liveMoveFromEntry(entry([routeFact]), players)).not.toHaveProperty("boosted");
  });

  it("reads a Space Cannon volley: shooters, dice, hits and the target fleet", () => {
    const shot = (zone: string, from: string, dice: number, hits: number): ActivityFact => ({
      type: "cannon_shot",
      player_id: "p1",
      value: "p2",
      delta: hits,
      detail: zone,
      route: [from, "000"],
      dice,
    });
    const twoPlayers = {
      ...players,
      p2: { faction: "hacan", color: "red", display_name: "P2", is_bot: false },
    };
    expect(
      liveMoveFromEntry(
        entry([shot("lodor", "000", 3, 2), shot("space", "101", 1, 0)], "spacecannon.fire"),
        twoPlayers,
      ),
    ).toEqual({
      kind: "cannon",
      faction: "sol",
      targetFaction: "hacan",
      active: "000",
      shots: [
        { position: "000", zone: "lodor", dice: 3, hits: 2 },
        { position: "101", zone: "space", dice: 1, hits: 0 },
      ],
    });
    // A pass carries no shots: nothing to replay.
    expect(liveMoveFromEntry(entry([], "spacecannon.fire"), twoPlayers)).toBeUndefined();
  });

  it("pairs a volley with the live map at once (it moves nothing)", () => {
    const volley: LiveMove = {
      kind: "cannon",
      faction: "sol",
      targetFaction: "hacan",
      active: "000",
      shots: [],
    };
    const live = data({ "000": 1 });
    expect(replayBaseline({ move: volley, liveAtArrival: live, previousAtArrival: undefined }, live)).toBe(live);
  });

  it("ignores entries without a route and other actions", () => {
    expect(liveMoveFromEntry(entry([]), players)).toBeUndefined();
    expect(
      liveMoveFromEntry(entry([routeFact], "tactical.produce"), players),
    ).toBeUndefined();
  });
});

describe("pairing a move with the live map", () => {
  const move: LiveMove = {
    kind: "move",
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

  it("still replays a move whose whole fleet a gravity rift swallowed", () => {
    const gone = data({ "202": 0, "000": 0 });
    expect(moveLanded(before, gone, move)).toBe(false);
    expect(
      moveLanded(before, gone, { ...move, lost: [{ unitId: "ca", count: 2, at: "101" }] }),
    ).toBe(true);
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

describe("pairing a landing with the live map", () => {
  const map = (space: number, planet: number): GameData =>
    ({
      tiles: {
        "000": {
          properties: { x: 0, y: 0 },
          planets: { lodor: {} },
          entityPlacements: [
            { entityType: "unit", entityId: "gf", faction: "sol", count: space, x: 0, y: 0 },
            {
              entityType: "unit",
              entityId: "gf",
              faction: "sol",
              count: planet,
              x: 0,
              y: 0,
              planetName: "lodor",
            },
          ].filter((stack) => stack.count > 0),
        },
      },
    }) as unknown as GameData;
  const landing: LiveMove = { kind: "landing", faction: "sol", planets: ["lodor"] };

  it("recognises units that left space for the planet", () => {
    expect(moveLanded(map(3, 0), map(1, 2), landing)).toBe(true);
    expect(moveLanded(map(3, 0), map(3, 0), landing)).toBe(false);
  });
});
