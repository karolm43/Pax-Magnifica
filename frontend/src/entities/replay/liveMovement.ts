import type { GameData } from "@/entities/game/types";
import type { Point } from "@/entities/data/types";
import { getGenericUnitDataByAsyncId } from "@/entities/lookup/units";
import { TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import {
  getPrintedLinkPoints,
  linkKindsOfToken,
} from "@/entities/geometry/wormholePoints";
import {
  PACK_MS,
  UNPACK_MS,
  flightPathDuration,
  type FlightAnomaly,
  type FlightLeg,
} from "@/entities/replay/flightPath";
import type {
  LiveFleetMove,
  LiveLanding,
  LiveMove,
  LocatedStack,
  PlannedMovement,
  ResolvedMovement,
  RiftLoss,
  StateCounts,
} from "@/entities/replay/types";
import {
  allUnitStacks,
  locatedKey,
  stackHolder,
  stateCount,
  statesForCount,
  subtractStates,
  unitStates,
} from "@/entities/replay/unitState";

/**
 * Live fleet moves (Activity `move_route`): which units flew, along which route, and how.
 *
 * The map snapshots before/after the move say WHAT moved (the faction's units that left
 * systems on the route); the Activity route says HOW (ordered systems, wormhole jumps,
 * anomalies). Fighters and ground forces pack into their carrier, ride inside it (mini
 * icons on the hull) and unpack when it lands. Landings (Activity `invasion.commit`) fly
 * ground forces from space down to their planets.
 */

/** Units that ride inside a carrier rather than flying on their own. */
const RIDING_CARGO = new Set(["gf", "mf", "ff"]);
/** Waypoints keep half of a ship's offset from its tile center, so a fleet holds formation. */
const FORMATION_KEEP = 0.5;

export function resolveLiveMovement(
  previous: GameData,
  current: GameData,
  move: LiveMove,
): ResolvedMovement | undefined {
  return move.kind === "landing"
    ? resolveLanding(previous, current, move)
    : resolveFleetMove(previous, current, move);
}

function resolveFleetMove(
  previous: GameData,
  current: GameData,
  move: LiveFleetMove,
): ResolvedMovement | undefined {
  const target = move.route.at(-1);
  if (!target || move.route.length < 2) return undefined;
  const onRoute = new Set(move.route);
  const after = new Map(
    allUnitStacks(current).map((located) => [locatedKey(located), located]),
  );
  const sources = new Map<string, ResolvedMovement["sources"][number]>();
  // Rift losses still to assign to the units that left (per unit type, rift by rift).
  const losses = (move.lost ?? []).map((loss) => ({ ...loss }));
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
    const { survivors, swallowed } = takeRiftLosses(losses, stack.entityId, left);
    if (stateCount(survivors) > 0) {
      source.units.push({ faction: move.faction, unitId: stack.entityId, states: survivors });
    }
    for (const { states, at } of swallowed) {
      source.units.push({ faction: move.faction, unitId: stack.entityId, states, lostAt: at });
    }
    sources.set(key, source);
  }
  if (sources.size === 0) return undefined;
  return { targetPosition: target, targetHolder: "space", sources: [...sources.values()] };
}

/**
 * Splits units that left a system into those that fly on and those a gravity rift swallows,
 * consuming the move's `losses` budget for this unit type.
 */
function takeRiftLosses(
  losses: RiftLoss[],
  unitId: string,
  left: StateCounts,
): { survivors: StateCounts; swallowed: { states: StateCounts; at: string }[] } {
  let survivors = left;
  const swallowed: { states: StateCounts; at: string }[] = [];
  for (const loss of losses) {
    if (loss.unitId !== unitId || loss.count <= 0) continue;
    const take = Math.min(loss.count, stateCount(survivors));
    if (take <= 0) break;
    const states = statesForCount(survivors, take);
    survivors = subtractStates(survivors, states);
    loss.count -= take;
    swallowed.push({ states, at: loss.at });
  }
  return { survivors, swallowed };
}

/** Position of the system holding any of `planets` (landings name planets, not systems). */
export function landingPosition(
  data: GameData,
  planets: string[],
): string | undefined {
  return Object.keys(data.tiles).find((position) =>
    planets.some((planet) => planet in (data.tiles[position].planets ?? {})),
  );
}

function statesAt(
  data: GameData,
  position: string,
  holder: string,
  faction: string,
): Map<string, StateCounts> {
  const found = new Map<string, StateCounts>();
  for (const located of allUnitStacks(data)) {
    if (
      located.position === position &&
      located.stack.faction === faction &&
      stackHolder(located.stack) === holder
    ) {
      found.set(located.stack.entityId, unitStates(located.stack));
    }
  }
  return found;
}

const NONE: StateCounts = [0, 0, 0, 0];

/**
 * Ground forces that left the active system's space for its planets: each planet's gain is
 * matched with the units that left space, so every stack lands on the planet it reached.
 */
function resolveLanding(
  previous: GameData,
  current: GameData,
  landing: LiveLanding,
): ResolvedMovement | undefined {
  const position = landingPosition(current, landing.planets);
  if (!position) return undefined;
  const { faction } = landing;
  const spaceBefore = statesAt(previous, position, "space", faction);
  const spaceAfter = statesAt(current, position, "space", faction);
  const leftSpace = new Map<string, number>();
  for (const [unitId, before] of spaceBefore) {
    const left = stateCount(before) - stateCount(spaceAfter.get(unitId) ?? NONE);
    if (left > 0) leftSpace.set(unitId, left);
  }
  const units: ResolvedMovement["sources"][number]["units"] = [];
  for (const planet of landing.planets) {
    const before = statesAt(previous, position, planet, faction);
    for (const [unitId, after] of statesAt(current, position, planet, faction)) {
      const gained = stateCount(after) - stateCount(before.get(unitId) ?? NONE);
      const available = leftSpace.get(unitId) ?? 0;
      const count = Math.min(gained, available);
      if (count <= 0) continue;
      leftSpace.set(unitId, available - count);
      units.push({
        faction,
        unitId,
        states: statesForCount(spaceBefore.get(unitId) ?? NONE, count),
        toHolder: planet,
      });
    }
  }
  if (units.length === 0) return undefined;
  return {
    targetPosition: position,
    targetHolder: "space",
    sources: [{ position, holder: "space", units }],
  };
}

/**
 * Flight legs of a live action: the route of a fleet move, or one slow hop from space down
 * to the planet for a landing.
 */
export function liveLegs(
  data: GameData,
  move: LiveMove,
  source: LocatedStack,
  arrival: Point,
): FlightLeg[] | undefined {
  return move.kind === "landing"
    ? [{ ...arrival, kind: "lane" }]
    : routeLegs(data, move, source, arrival);
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

function anomalyAt(move: LiveFleetMove, position: string): FlightAnomaly | undefined {
  const names = move.anomalies[position] ?? [];
  if (names.includes("GRAVITY_RIFT")) return "rift";
  if (names.includes("NEBULA")) return "nebula";
  // Reachable only with a tech / ability (Antimass Deflectors, passing supernovas).
  if (names.includes("ASTEROID_FIELD")) return "asteroid";
  if (names.includes("SUPERNOVA")) return "supernova";
  return undefined;
}

/**
 * Flight legs from `source` (its own system on the route; cargo picked up on the way starts
 * mid-route) to `arrival`. Undefined when the route cannot be laid out on this map.
 */
export function routeLegs(
  data: GameData,
  move: LiveFleetMove,
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
    // Fracture ingress -> egress tears differ from a wormhole swirl.
    legs.push({ ...exit, kind: hop === "portal" ? "portal" : "jump" });
    if (last) legs.push({ ...arrival, kind: "lane", anomaly });
  }
  return legs.length > 0 ? legs : undefined;
}

/**
 * Flight of a ship that failed its gravity rift roll: along the route up to the rift (in
 * formation), then a `swallow` leg into the rift's center. A ship lost leaving the rift it
 * started in spirals in from where it stands. Undefined when the rift is not on this map.
 */
export function swallowLegs(
  data: GameData,
  move: LiveFleetMove,
  source: LocatedStack,
  rift: string,
): FlightLeg[] | undefined {
  const center = tileCenter(data, rift);
  const sourceCenter = tileCenter(data, source.position);
  const riftIndex = move.route.indexOf(rift);
  const startIndex = move.route.indexOf(source.position);
  if (!center || !sourceCenter || riftIndex < 0) return undefined;
  const swallow: FlightLeg = { ...center, kind: "swallow" };
  if (startIndex < 0 || riftIndex <= startIndex) return [swallow];
  const caught = {
    x: center.x + (source.worldX - sourceCenter.x) * FORMATION_KEEP,
    y: center.y + (source.worldY - sourceCenter.y) * FORMATION_KEEP,
  };
  const toRift: LiveFleetMove = {
    ...move,
    route: move.route.slice(0, riftIndex + 1),
    hops: move.hops.slice(0, riftIndex),
  };
  const legs = routeLegs(data, toRift, source, caught);
  return legs ? [...legs, swallow] : undefined;
}

function capacityOf(unitId: string): number {
  return getGenericUnitDataByAsyncId(unitId)?.capacityValue ?? 0;
}

function flightMs(movement: PlannedMovement): number {
  const { transition } = movement;
  return transition.flightPath
    ? flightPathDuration(
        { x: transition.stack.x, y: transition.stack.y },
        transition.flightPath,
      )
    : 0;
}

/**
 * Launch order of a fleet: the screen (destroyers) breaks orbit first, the capital ships
 * follow in waves, the flagship / war sun last. Unlisted ships launch with the cruisers.
 */
const LAUNCH_WAVE: Record<string, number> = { dd: 0, ca: 1, cv: 2, dn: 3, fs: 4, ws: 4 };
export const LAUNCH_WAVE_MS = 260;

/**
 * A fleet does not lift off as one block: each class of ship launches as a wave
 * `LAUNCH_WAVE_MS` after the previous one, so the move reads as a war fleet getting under
 * way (user decision). Cargo is not a wave: it rides inside its carrier.
 */
export function staggerFleetLaunch(movements: PlannedMovement[]): void {
  const ships = movements.filter((m) => !RIDING_CARGO.has(m.source.unitId));
  const waves = [...new Set(ships.map((m) => LAUNCH_WAVE[m.source.unitId] ?? 1))].sort(
    (a, b) => a - b,
  );
  for (const movement of ships) {
    const wave = waves.indexOf(LAUNCH_WAVE[movement.source.unitId] ?? 1);
    movement.transition.delayMs = (movement.transition.delayMs ?? 0) + wave * LAUNCH_WAVE_MS;
  }
}

/**
 * Fighters and ground forces pack into a moving ship with capacity (preferably one leaving
 * the same system): they slip under its hull and vanish, the fleet launches once they are
 * aboard, nothing of them is drawn in flight, and they unpack from the carrier once it lands.
 */
export function packRidingCargo(movements: PlannedMovement[]): void {
  const carriers = movements.filter(
    (movement) =>
      capacityOf(movement.source.unitId) > 0 &&
      !RIDING_CARGO.has(movement.source.unitId),
  );
  const cargo = movements.filter((movement) =>
    RIDING_CARGO.has(movement.source.unitId),
  );
  if (carriers.length === 0 || cargo.length === 0) return;
  // Every ship waits for the cargo to board, so the fleet still leaves together.
  for (const movement of movements) {
    if (RIDING_CARGO.has(movement.source.unitId)) continue;
    movement.transition.delayMs = (movement.transition.delayMs ?? 0) + PACK_MS;
  }
  for (const item of cargo) {
    // Cargo lost in a rift rides a doomed carrier; survivors ride one that gets through.
    const fellow = carriers.filter((c) => !c.lostAt === !item.lostAt);
    const pool = fellow.length > 0 ? fellow : carriers;
    const carrier =
      pool.find((c) => c.source.position === item.source.position) ?? pool[0];
    const { transition } = item;
    const sameSystem = carrier.source.position === item.source.position;
    // Hidden from boarding until the carrier (launching in its own wave) has landed.
    const boardedAt = (transition.delayMs ?? 0) + PACK_MS;
    const landedAt = (carrier.transition.delayMs ?? 0) + flightMs(carrier);
    transition.cargoRide = {
      // Mid-route pickups board where they stand (the carrier passes by later).
      boardX: sameSystem ? carrier.transition.stack.x : transition.stack.x,
      boardY: sameSystem ? carrier.transition.stack.y : transition.stack.y,
      landX: carrier.transition.toX,
      landY: carrier.transition.toY,
      packMs: PACK_MS,
      rideMs: Math.max(0, landedAt - boardedAt),
      unpackMs: UNPACK_MS,
      ...(item.lostAt ? { lost: true } : {}),
    };
    transition.flightPath = undefined;
  }
}
