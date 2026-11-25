import type { ActivityEntry, ActivityPlayer } from "@/api/boardQueries";
import type { GameData } from "@/entities/game/types";
import { landingPosition } from "@/entities/replay/liveMovement";
import type { LiveMove, RiftLoss } from "@/entities/replay/types";
import { BASE_TYPE_BY_ASYNC } from "@/domains/map/components/UnitStack/cargo";
import {
  allUnitStacks,
  stackHolder,
  stateCount,
  unitStates,
} from "@/entities/replay/unitState";

/**
 * Live board replays: every client turns a new Activity entry into the same animation on its
 * own map - a fleet move (`tactical.move` with a `move_route` fact) or a landing
 * (`invasion.commit` with `landed` facts). Pure helpers live here; `useLiveMoveReplay` pairs
 * the entry with the map data before and after it.
 */

/** The live action an Activity entry announces, or undefined when there is none to replay. */
export function liveMoveFromEntry(
  entry: ActivityEntry,
  players: Record<string, ActivityPlayer>,
): LiveMove | undefined {
  const activity = entry.activity;
  if (!activity.actor_id) return undefined;
  const faction = players[activity.actor_id]?.faction;
  if (!faction) return undefined;
  if (activity.action === "spacecannon.fire") {
    const shots = activity.facts.filter(
      (f) => f.type === "cannon_shot" && f.route && f.route.length === 2 && f.value,
    );
    const targetFaction = players[shots[0]?.value ?? ""]?.faction;
    const active = shots[0]?.route?.[1];
    if (!targetFaction || !active) return undefined;
    return {
      kind: "cannon",
      faction,
      targetFaction,
      active,
      shots: shots.map((f) => ({
        position: f.route![0],
        zone: f.detail ?? "space",
        dice: f.dice ?? f.delta ?? 0,
        hits: f.delta ?? 0,
      })),
    };
  }
  if (activity.action === "invasion.commit") {
    const planets = [
      ...new Set(
        activity.facts
          .filter((f) => f.type === "landed" && f.detail)
          .map((f) => f.detail as string),
      ),
    ];
    return planets.length > 0 ? { kind: "landing", faction, planets } : undefined;
  }
  if (activity.action !== "tactical.move") return undefined;
  const fact = activity.facts.find((f) => f.type === "move_route");
  const route = fact?.route;
  if (!route || route.length < 2) return undefined;
  const lost = riftLosses(activity.facts);
  const boosted = activity.facts.flatMap((f) =>
    f.type === "gravity_drive" && f.value ? [ASYNC_BY_BASE_TYPE[f.value] ?? f.value] : [],
  );
  return {
    kind: "move",
    faction,
    route: [...route],
    hops: [...(fact.hops ?? [])],
    anomalies: { ...(fact.anomalies ?? {}) },
    ...(lost.length > 0 ? { lost } : {}),
    ...(boosted.length > 0 ? { boosted } : {}),
  };
}

const ASYNC_BY_BASE_TYPE = Object.fromEntries(
  Object.entries(BASE_TYPE_BY_ASYNC).map(([asyncId, baseType]) => [baseType, asyncId]),
);

/** Ships / cargo a gravity rift swallowed on the move (`rift_lost` facts), as map unit ids. */
function riftLosses(facts: ActivityEntry["activity"]["facts"]): RiftLoss[] {
  return facts.flatMap((f) =>
    f.type === "rift_lost" && f.value && f.detail && (f.delta ?? 0) > 0
      ? [{ unitId: ASYNC_BY_BASE_TYPE[f.value] ?? f.value, count: f.delta!, at: f.detail }]
      : [],
  );
}

/** Systems to highlight while the action replays. */
export function livePositions(move: LiveMove, data: GameData | undefined): string[] {
  if (move.kind === "move") return move.route;
  if (move.kind === "cannon") return [...new Set([move.active, ...move.shots.map((s) => s.position)])];
  const position = data && landingPosition(data, move.planets);
  return position ? [position] : [];
}

function unitsAt(
  data: GameData,
  faction: string,
  position: string,
  holders: (holder: string) => boolean,
): number {
  return allUnitStacks(data)
    .filter(
      (located) =>
        located.position === position &&
        located.stack.faction === faction &&
        holders(stackHolder(located.stack)),
    )
    .reduce((total, located) => total + stateCount(unitStates(located.stack)), 0);
}

const inSpace = (holder: string) => holder === "space";
const anywhere = () => true;

/**
 * Whether `before` -> `after` is exactly this action. A move: the faction lost units in the
 * route's source system and gained units in the destination's space. A landing: units left
 * space and reached the named planets. Guards against pairing the entry with an unrelated
 * refresh (e.g. an earlier move into the same active system).
 */
export function moveLanded(before: GameData, after: GameData, move: LiveMove): boolean {
  if (move.kind === "cannon") return true; // a volley moves nothing: any map pairs with it
  if (move.kind === "landing") {
    const position = landingPosition(after, move.planets);
    if (!position) return false;
    const onPlanets = (holder: string) => move.planets.includes(holder);
    return (
      unitsAt(after, move.faction, position, inSpace) <
        unitsAt(before, move.faction, position, inSpace) &&
      unitsAt(after, move.faction, position, onPlanets) >
        unitsAt(before, move.faction, position, onPlanets)
    );
  }
  const source = move.route[0];
  const target = move.route[move.route.length - 1];
  // A gravity rift may swallow the whole fleet: then nothing arrives at the target.
  const arrived =
    unitsAt(after, move.faction, target, inSpace) >
      unitsAt(before, move.faction, target, inSpace) || (move.lost?.length ?? 0) > 0;
  return (
    unitsAt(after, move.faction, source, anywhere) <
      unitsAt(before, move.faction, source, anywhere) && arrived
  );
}

export type PendingLiveMove = {
  move: LiveMove;
  /** Live map when the entry arrived, and the one before it. */
  liveAtArrival: GameData | undefined;
  previousAtArrival: GameData | undefined;
};

/**
 * The map state before the action, once the live map shows it - or undefined to keep
 * waiting. The feed and the map refresh separately after a push, in either order.
 */
export function replayBaseline(
  pending: PendingLiveMove,
  live: GameData | undefined,
): GameData | undefined {
  if (!live) return undefined;
  const { move, liveAtArrival, previousAtArrival } = pending;
  if (move.kind === "cannon") return live;
  if (liveAtArrival && live !== liveAtArrival) {
    return moveLanded(liveAtArrival, live, move) ? liveAtArrival : undefined;
  }
  if (previousAtArrival && moveLanded(previousAtArrival, live, move)) return previousAtArrival;
  return undefined;
}
