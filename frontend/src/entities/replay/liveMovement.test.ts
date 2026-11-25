import { describe, expect, it } from "vitest";
import type { GameData } from "@/entities/game/types";
import type { EntityStack } from "@/entities/positioning";
import {
  buildMapReplayPlan,
  replayRunDuration,
} from "./historicalMapTransitions";
import type { LiveCannon, LiveFleetMove, LiveMove } from "./types";
import { CANNON_DICE_LEAD_MS } from "./cannonVolley";
import { PACK_MS, flightPathDuration } from "./flightPath";
import { LAUNCH_WAVE_MS } from "./liveMovement";
import { getPrintedLinkPoints } from "@/entities/geometry/wormholePoints";

type TileSpec = {
  x: number;
  y: number;
  units: EntityStack[];
  systemId?: string;
};

/** Minimal map: tiles at fixed world positions with unit stacks (tile-local x/y). */
function map(tiles: Record<string, TileSpec>): GameData {
  return {
    tiles: Object.fromEntries(
      Object.entries(tiles).map(([position, tile]) => [
        position,
        {
          position,
          systemId: tile.systemId ?? "1",
          properties: { x: tile.x, y: tile.y },
          entityPlacements: tile.units,
          commandCounters: [],
          planets: {},
          tokens: [],
        },
      ]),
    ),
    originalFactionColorMap: {},
  } as unknown as GameData;
}

function unit(entityId: string, count: number, x = 150, y = 150): EntityStack {
  return {
    entityType: "unit",
    entityId,
    faction: "sol",
    count,
    x,
    y,
  } as EntityStack;
}

const POSITIONS: Record<string, { x: number; y: number }> = {
  "202": { x: 0, y: 600 },
  "101": { x: 0, y: 300 },
  "000": { x: 0, y: 0 },
};

function line(units: Record<string, EntityStack[]>): GameData {
  return map(
    Object.fromEntries(
      Object.entries(POSITIONS).map(([position, at]) => [
        position,
        { ...at, units: units[position] ?? [] },
      ]),
    ),
  );
}

const move = (overrides: Partial<LiveFleetMove> = {}): LiveMove => ({
  kind: "move",
  faction: "sol",
  route: ["202", "101", "000"],
  hops: ["lane", "lane"],
  anomalies: {},
  ...overrides,
});

const moved = (plan: ReturnType<typeof buildMapReplayPlan>, unitId = "ca") =>
  plan.transitions.find(
    (t) => t.kind === "moved" && t.stack.entityId === unitId,
  );

describe("buildMapReplayPlan with a live move", () => {
  it("flies the ship through every system of the route", () => {
    const plan = buildMapReplayPlan(
      line({ "202": [unit("ca", 1)] }),
      line({ "000": [unit("ca", 1)] }),
      { liveMove: move(), activeFaction: "sol" },
    );
    const flight = moved(plan);
    expect(flight?.flightPath).toHaveLength(2);
    const [via, landing] = flight!.flightPath!;
    // Waypoint by the center of 101 (tile at 0,300 -> center 172.5,449.5).
    expect(via.kind).toBe("lane");
    expect(Math.abs(via.y - 449.5)).toBeLessThan(40);
    expect(landing).toMatchObject({ x: flight!.toX, y: flight!.toY });
    expect(plan.durationMs).toBeGreaterThan(0);
  });

  it("flies a one-hop live move along a path too (slow live pacing)", () => {
    const plan = buildMapReplayPlan(
      line({ "101": [unit("ca", 1)] }),
      line({ "000": [unit("ca", 1)] }),
      {
        liveMove: move({ route: ["101", "000"], hops: ["lane"] }),
        activeFaction: "sol",
      },
    );
    expect(moved(plan)?.flightPath).toHaveLength(1);
  });

  it("jumps through a wormhole with swirls at both ends", () => {
    const plan = buildMapReplayPlan(
      line({ "202": [unit("ca", 1)] }),
      line({ "000": [unit("ca", 1)] }),
      {
        liveMove: move({ route: ["202", "000"], hops: ["wormhole"] }),
        activeFaction: "sol",
      },
    );
    expect(moved(plan)?.flightPath?.some((leg) => leg.kind === "jump")).toBe(
      true,
    );
    const kinds = plan.flightEffects.map((e) => e.kind);
    expect(kinds).toContain("wormholeIn");
    expect(kinds).toContain("wormholeOut");
  });

  it("crosses a Fracture ingress/egress as a portal tear, not a wormhole swirl", () => {
    const plan = buildMapReplayPlan(
      line({ "202": [unit("ca", 1)] }),
      line({ "000": [unit("ca", 1)] }),
      {
        liveMove: move({ route: ["202", "000"], hops: ["portal"] }),
        activeFaction: "sol",
      },
    );
    const legs = moved(plan)!.flightPath!;
    expect(legs.some((leg) => leg.kind === "portal")).toBe(true);
    expect(legs.some((leg) => leg.kind === "jump")).toBe(false);
    const kinds = plan.flightEffects.map((e) => e.kind);
    expect(kinds).toEqual(expect.arrayContaining(["portalIn", "portalOut"]));
    expect(kinds).not.toContain("wormholeIn");
  });

  it("marks asteroid fields and supernovas on the route", () => {
    const plan = buildMapReplayPlan(
      line({ "202": [unit("ca", 1)] }),
      line({ "000": [unit("ca", 1)] }),
      {
        liveMove: move({
          anomalies: { "101": ["ASTEROID_FIELD"], "000": ["SUPERNOVA"] },
        }),
        activeFaction: "sol",
      },
    );
    expect(moved(plan)!.flightPath!.map((leg) => leg.anomaly)).toEqual([
      "asteroid",
      "supernova",
    ]);
    const kinds = plan.flightEffects.map((e) => e.kind);
    expect(kinds).toEqual(expect.arrayContaining(["asteroidDust", "supernovaFlare"]));
  });

  it("wraps a Gravity Drive ship in its field and opens a gravity well at launch", () => {
    const plan = buildMapReplayPlan(
      line({ "202": [unit("ca", 1)] }),
      line({ "000": [unit("ca", 1)] }),
      { liveMove: move({ boosted: ["ca"] }), activeFaction: "sol" },
    );
    expect(moved(plan)?.gravityDrive).toBe(true);
    expect(plan.flightEffects.find((e) => e.kind === "gravityDrive")).toMatchObject({
      delayMs: moved(plan)?.delayMs ?? 0,
    });
    const plain = buildMapReplayPlan(
      line({ "202": [unit("ca", 1)] }),
      line({ "000": [unit("ca", 1)] }),
      { liveMove: move(), activeFaction: "sol" },
    );
    expect(moved(plain)?.gravityDrive).toBeUndefined();
    expect(plain.flightEffects.map((e) => e.kind)).not.toContain("gravityDrive");
  });

  it("enters and leaves through the wormholes printed on the tiles", () => {
    // 39 = Alpha Wormhole (empty), 26 = Lodor (alpha wormhole).
    const tiles = (units: Record<string, EntityStack[]>) =>
      map({
        "202": { x: 0, y: 600, systemId: "39", units: units["202"] ?? [] },
        "000": { x: 0, y: 0, systemId: "26", units: units["000"] ?? [] },
      });
    const plan = buildMapReplayPlan(
      tiles({ "202": [unit("ca", 1)] }),
      tiles({ "000": [unit("ca", 1)] }),
      {
        liveMove: move({ route: ["202", "000"], hops: ["wormhole"] }),
        activeFaction: "sol",
      },
    );
    const [entry] = getPrintedLinkPoints("39");
    const [exit] = getPrintedLinkPoints("26");
    const into = plan.flightEffects.find((e) => e.kind === "wormholeIn");
    const out = plan.flightEffects.find((e) => e.kind === "wormholeOut");
    expect(into).toMatchObject({ x: entry.x, y: 600 + entry.y });
    expect(out).toMatchObject({ x: exit.x, y: exit.y });
  });

  it("marks a gravity rift on the route", () => {
    const plan = buildMapReplayPlan(
      line({ "202": [unit("ca", 1)] }),
      line({ "000": [unit("ca", 1)] }),
      {
        liveMove: move({ anomalies: { "101": ["GRAVITY_RIFT"] } }),
        activeFaction: "sol",
      },
    );
    expect(plan.flightEffects.map((e) => e.kind)).toContain("riftWarp");
  });

  it("packs fighters and infantry into the carrier and unpacks them on landing", () => {
    const plan = buildMapReplayPlan(
      line({
        "202": [unit("cv", 1), unit("gf", 2, 200, 180), unit("ff", 3, 110, 190)],
      }),
      line({
        "000": [unit("cv", 1), unit("gf", 2, 200, 180), unit("ff", 3, 110, 190)],
      }),
      { liveMove: move(), activeFaction: "sol" },
    );
    const carrier = moved(plan, "cv")!;
    // The fleet launches once the cargo is aboard.
    expect(carrier.delayMs).toBe(PACK_MS);
    for (const id of ["gf", "ff"]) {
      const ride = moved(plan, id)?.cargoRide;
      expect(ride).toMatchObject({
        boardX: carrier.stack.x,
        boardY: carrier.stack.y,
        landX: carrier.toX,
        landY: carrier.toY,
        packMs: PACK_MS,
      });
      expect(moved(plan, id)?.flightPath).toBeUndefined();
    }
  });

  it("launches the fleet in waves and keeps cargo hidden until its carrier lands", () => {
    const units = [unit("dd", 1, 90, 90), unit("cv", 1), unit("gf", 2, 200, 180)];
    const plan = buildMapReplayPlan(line({ "202": units }), line({ "000": units }), {
      liveMove: move(),
      activeFaction: "sol",
    });
    const destroyer = moved(plan, "dd")!;
    const carrier = moved(plan, "cv")!;
    // Destroyers screen ahead; the carrier follows one wave later.
    expect(destroyer.delayMs).toBe(PACK_MS);
    expect(carrier.delayMs).toBe(PACK_MS + LAUNCH_WAVE_MS);
    // Infantry unpacks exactly when its (later) carrier has landed.
    const infantry = moved(plan, "gf")!;
    const ride = infantry.cargoRide!;
    const carrierLanded =
      carrier.delayMs! +
      flightPathDuration({ x: carrier.stack.x, y: carrier.stack.y }, carrier.flightPath!);
    expect((infantry.delayMs ?? 0) + ride.packMs + ride.rideMs).toBe(carrierLanded);
  });

  it("flies a ship lost in a gravity rift to the rift and swallows it there", () => {
    const plan = buildMapReplayPlan(
      line({ "202": [unit("ca", 2)] }),
      line({ "000": [unit("ca", 1)] }),
      {
        liveMove: move({
          anomalies: { "101": ["GRAVITY_RIFT"] },
          lost: [{ unitId: "ca", count: 1, at: "101" }],
        }),
        activeFaction: "sol",
      },
    );
    const flights = plan.transitions.filter(
      (t) => t.kind === "moved" && t.stack.entityId === "ca",
    );
    expect(flights).toHaveLength(2);
    const doomed = flights.find((t) => t.flightPath?.at(-1)?.kind === "swallow")!;
    const survivor = flights.find((t) => t !== doomed)!;
    // Swallowed at the center of 101 (tile at 0,300 -> center 172.5,449.5).
    expect(doomed.flightPath!.at(-1)).toMatchObject({ x: 172.5, y: 449.5 });
    expect(doomed.stack.count).toBe(1);
    expect(survivor.flightPath!.at(-1)).toMatchObject({ x: survivor.toX, y: survivor.toY });
    expect(plan.flightEffects.map((e) => e.kind)).toContain("blackHole");
    // Nothing fades out at the target: the lost ship never counted as arriving there.
    expect(plan.transitions.filter((t) => t.kind === "removed" && !t.sourceHold)).toEqual([]);
  });

  it("sinks the cargo of a swallowed carrier with it", () => {
    const units = [unit("cv", 1), unit("gf", 2, 200, 180)];
    const plan = buildMapReplayPlan(line({ "202": units }), line({}), {
      liveMove: move({
        anomalies: { "202": ["GRAVITY_RIFT"] },
        lost: [
          { unitId: "cv", count: 1, at: "202" },
          { unitId: "gf", count: 2, at: "202" },
        ],
      }),
      activeFaction: "sol",
    });
    // Lost leaving the rift it started in: it spirals in right where it stands.
    expect(moved(plan, "cv")!.flightPath).toEqual([
      { x: 172.5, y: 749.5, kind: "swallow" },
    ]);
    expect(moved(plan, "gf")!.cargoRide).toMatchObject({ lost: true });
  });

  it("flies ground forces from space down to the planets of an invasion", () => {
    const tiles = (space: EntityStack[], planet: EntityStack[]) =>
      ({
        tiles: {
          "000": {
            position: "000",
            systemId: "1",
            properties: { x: 0, y: 0 },
            entityPlacements: [...space, ...planet],
            commandCounters: [],
            planets: { lodor: {} },
            tokens: [],
          },
        },
        originalFactionColorMap: {},
      }) as unknown as GameData;
    const onPlanet = (entityId: string, count: number) =>
      ({ ...unit(entityId, count, 240, 120), planetName: "lodor" }) as EntityStack;
    const plan = buildMapReplayPlan(
      tiles([unit("cv", 1), unit("gf", 3, 200, 180)], []),
      tiles([unit("cv", 1), unit("gf", 1, 200, 180)], [onPlanet("gf", 2)]),
      {
        liveMove: { kind: "landing", faction: "sol", planets: ["lodor"] },
        activeFaction: "sol",
      },
    );
    const landing = moved(plan, "gf");
    expect(landing?.stack.count).toBe(2);
    expect(landing?.flightPath).toHaveLength(1);
    expect(landing).toMatchObject({ toX: 240, toY: 120 });
    expect(moved(plan, "cv")).toBeUndefined();
  });
});

describe("replayRunDuration", () => {
  it("is zero under admin fast mode or reduced motion", () => {
    const plan = { durationMs: 1800 };
    const run = (adminFastMode: boolean, reducedMotion: boolean) =>
      replayRunDuration(plan, { adminFastMode, reducedMotion });
    expect(run(false, false)).toBe(1800);
    expect(run(true, false)).toBe(0);
    expect(run(false, true)).toBe(0);
  });
});

describe("Space Cannon volley replay", () => {
  const volley = (shots: LiveCannon["shots"]): LiveMove => ({
    kind: "cannon",
    faction: "hacan",
    targetFaction: "sol",
    active: "000",
    shots,
  });
  const fleet = line({ "000": [unit("ca", 2)] });

  it("fires one bolt per die after the dice land and flashes only on hits", () => {
    const plan = buildMapReplayPlan(fleet, fleet, {
      liveMove: volley([{ position: "101", zone: "space", dice: 3, hits: 1 }]),
    });
    expect(plan.transitions).toEqual([]);
    expect(plan.lasers).toHaveLength(3);
    expect(plan.lasers.every((l) => l.color === "cannon")).toBe(true);
    expect(Math.min(...plan.lasers.map((l) => l.delayMs))).toBe(CANNON_DICE_LEAD_MS);
    const kinds = plan.flightEffects.map((e) => e.kind);
    expect(kinds.filter((k) => k === "cannonFlash")).toHaveLength(3);
    expect(kinds.filter((k) => k === "cannonImpact")).toHaveLength(1);
    // The hit strikes the target fleet exactly; the misses sail wide of it.
    const [hit, ...misses] = plan.lasers;
    const strike = plan.flightEffects.find((e) => e.kind === "cannonImpact")!;
    expect({ x: hit.toX, y: hit.toY }).toEqual({ x: strike.x, y: strike.y });
    expect(misses.every((l) => l.toX !== hit.toX || l.toY !== hit.toY)).toBe(true);
    expect(plan.durationMs).toBeGreaterThan(CANNON_DICE_LEAD_MS);
  });

  it("caps a huge volley but still strikes with every drawn bolt that hit", () => {
    const plan = buildMapReplayPlan(fleet, fleet, {
      liveMove: volley([{ position: "101", zone: "space", dice: 20, hits: 20 }]),
    });
    expect(plan.lasers.length).toBeLessThanOrEqual(16);
    expect(plan.flightEffects.filter((e) => e.kind === "cannonImpact")).toHaveLength(
      plan.lasers.length,
    );
  });

  it("draws nothing for an empty volley", () => {
    const plan = buildMapReplayPlan(fleet, fleet, {
      liveMove: { ...(volley([]) as LiveCannon), shots: [] },
    });
    expect(plan.lasers).toEqual([]);
    expect(plan.durationMs).toBe(0);
  });
});
