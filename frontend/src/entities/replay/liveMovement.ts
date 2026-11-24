import type { GameData } from "@/entities/game/types";
import type { Point } from "@/entities/data/types";
import { getGenericUnitDataByAsyncId } from "@/entities/lookup/units";
import { TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import {
  getPrintedLinkPoints,
  linkKindsOfToken,
} from "@/entities/geometry/wormholePoints";
import type { FlightAnomaly, FlightLeg } from "@/entities/replay/flightPath";
import type {
  LiveMove,
  LocatedStack,
  PlannedMovement,
  ResolvedMovement,
} from "@/entities/replay/types";
import {
  allUnitStacks,
  locatedKey,
  stackHolder,
  stateCount,
  subtractStates,
  unitStates,
} from "@/entities/replay/unitState";

/**
 * Live fleet moves (Activity `move_route`): which units flew, along which route, and how.
 *
 * The map snapshots before/after the move say WHAT moved (the faction's units that left
 * systems on the route); the Activity route says HOW (ordered systems, wormhole jumps,
 * anomalies). Ground forces travel inside their carrier: hidden in flight, shown as mini
 * badges on the ship, landing with it.
 */

/** Units that ride inside a carrier rather than flying on their own. */
const RIDING_CARGO = new Set(["gf", "mf"]);
/** Waypoints keep half of a ship's offset from its tile center, so a fleet holds formation. */
const FORMATION_KEEP = 0.5;

export function resolveLiveMovement(
  previous: GameData,
  current: GameData,
  move: LiveMove,
): ResolvedMovement | undefined {
  const target = move.route.at(-1);
  if (!target || move.route.length < 2) return undefined;
  const onRoute = new Set(move.route);
  const after = new Map(
    allUnitStacks(current).map((located) => [locatedKey(located), located]),
  );
  const sources = new Map<string, ResolvedMovement["sources"][number]>();
  for (const located of allUnitStacks(previous)) {
    const { stack, position } = located;
    if (stack.faction !== move.faction || !onRoute.has(position)) continue;
    const holder = stackHolder(stack);
    // Units already in the destination's space did not move; its planets can load cargo.
    if (position === target && holder === "space") continue;
    const remaining = after.get(locatedKey(located));
    const left = subtractStates(
      unitStates(stack),
      remaining ? unitStates(remaining.stack) : [0, 0, 0, 0],
    );
    if (stateCount(left) === 0) continue;
    const key = `${position}\u0000${holder}`;
    const source = sources.get(key) ?? { position, holder, units: [] };
    source.units.push({ faction: move.faction, unitId: stack.entityId, states: left });
    sources.set(key, source);
  }
  if (sources.size === 0) return undefined;
  return { targetPosition: target, targetHolder: "space", sources: [...sources.values()] };
}

function tileCenter(data: GameData, position: string): Point | undefined {
  const tile = data.tiles[position];
  if (!tile) return undefined;
  return {
    x: tile.properties.x + TILE_WIDTH / 2,
    y: tile.properties.y + TILE_HEIGHT / 2,
  };
}

type Gate = Point & { kinds: string[] };

/** Wormholes / gates of a system in world coordinates: tokens first, then printed ones. */
function gatesAt(data: GameData, position: string): Gate[] {
  const tile = data.tiles[position];
  if (!tile) return [];
  const { x, y } = tile.properties;
  const tokens = tile.entityPlacements.flatMap((stack) => {
    if (stack.entityType !== "token") return [];
    const kinds = linkKindsOfToken(stack.entityId);
    return kinds.length > 0 ? [{ x: x + stack.x, y: y + stack.y, kinds }] : [];
  });
  const printed = getPrintedLinkPoints(tile.systemId).map((point) => ({
    x: x + point.x,
    y: y + point.y,
    kinds: point.kinds,
  }));
  return [...tokens, ...printed];
}

/** Same wormhole type, or an ingress leading to an egress (and back). */
function kindsLink(a: string, b: string): boolean {
  return (
    a === b ||
    (a === "INGRESS" && b === "EGRESS") ||
    (a === "EGRESS" && b === "INGRESS")
  );
}

/**
 * The board spots a wormhole hop goes through: the matching wormhole (printed on the tile or
 * a token) in each system. Undefined when the map shows none (hook-granted adjacency).
 */
export function wormholeGates(
  data: GameData,
  from: string,
  to: string,
): { entry: Point; exit: Point } | undefined {
  const exits = gatesAt(data, to);
  for (const entry of gatesAt(data, from)) {
    const exit = exits.find((candidate) =>
      entry.kinds.some((kind) => candidate.kinds.some((other) => kindsLink(kind, other))),
    );
    if (exit) return { entry: { x: entry.x, y: entry.y }, exit: { x: exit.x, y: exit.y } };
  }
  return undefined;
}

function anomalyAt(move: LiveMove, position: string): FlightAnomaly | undefined {
  const names = move.anomalies[position] ?? [];
  if (names.includes("GRAVITY_RIFT")) return "rift";
  if (names.includes("NEBULA")) return "nebula";
  return undefined;
}

/**
 * Flight legs from `source` (its own system on the route; cargo picked up on the way starts
 * mid-route) to `arrival`. Undefined when the route cannot be laid out on this map.
 */
export function routeLegs(
  data: GameData,
  move: LiveMove,
  source: LocatedStack,
  arrival: Point,
): FlightLeg[] | undefined {
  const startIndex = move.route.indexOf(source.position);
  const sourceCenter = tileCenter(data, source.position);
  if (startIndex < 0 || !sourceCenter) return undefined;
  const offset = {
    x: (source.worldX - sourceCenter.x) * FORMATION_KEEP,
    y: (source.worldY - sourceCenter.y) * FORMATION_KEEP,
  };
  const waypoint = (position: string): Point | undefined => {
    const center = tileCenter(data, position);
    return center && { x: center.x + offset.x, y: center.y + offset.y };
  };
  const legs: FlightLeg[] = [];
  for (let index = startIndex; index < move.route.length - 1; index += 1) {
    const from = move.route[index];
    const to = move.route[index + 1];
    const last = index + 1 === move.route.length - 1;
    const anomaly = anomalyAt(move, to);
    const hop = move.hops[index] ?? "lane";
    if (hop === "lane") {
      const point = last ? arrival : waypoint(to);
      if (!point) return undefined;
      legs.push({ ...point, kind: "lane", anomaly });
      continue;
    }
    // Wormhole / ingress-egress: fly to the gate on the board, vanish, emerge at the linked
    // gate. Adjacency without a visible gate (Lost Star Chart, Conduit) jumps between centers.
    const gates = wormholeGates(data, from, to);
    const gate = gates?.entry ?? waypoint(from);
    const exit = gates?.exit ?? waypoint(to);
    if (!gate || !exit) return undefined;
    const atGate = legs.length === 0 ? source : undefined;
    const alreadyThere =
      atGate !== undefined &&
      Math.hypot(atGate.worldX - gate.x, atGate.worldY - gate.y) < 1;
    if (!alreadyThere) legs.push({ ...gate, kind: "lane" });
    legs.push({ ...exit, kind: "jump" });
    if (last) legs.push({ ...arrival, kind: "lane", anomaly });
  }
  return legs.length > 0 ? legs : undefined;
}

function capacityOf(unitId: string): number {
  return getGenericUnitDataByAsyncId(unitId)?.capacityValue ?? 0;
}

/**
 * Ground forces ride inside a moving ship with capacity: their own transitions are hidden in
 * flight (they land with the fleet) and the carrier shows them as mini badges.
 */
export function attachRidingCargo(movements: PlannedMovement[]): void {
  const carrier = movements.find(
    (movement) =>
      capacityOf(movement.source.unitId) > 0 &&
      !RIDING_CARGO.has(movement.source.unitId),
  );
  if (!carrier) return;
  const cargo = new Map<string, number>();
  for (const movement of movements) {
    if (!RIDING_CARGO.has(movement.source.unitId)) continue;
    movement.transition.hiddenInFlight = true;
    const count = stateCount(unitStates(movement.transition.stack));
    cargo.set(movement.source.unitId, (cargo.get(movement.source.unitId) ?? 0) + count);
  }
  if (cargo.size === 0) return;
  carrier.transition.carriedCargo = [...cargo.entries()].map(([unitId, count]) => ({
    unitId,
    count,
  }));
}
