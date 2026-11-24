import type { ActivityEntry, ActivityPlayer } from "@/api/boardQueries";
import type { GameData } from "@/entities/game/types";
import { landingPosition } from "@/entities/replay/liveMovement";
import type { LiveMove } from "@/entities/replay/types";
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
  return {
    kind: "move",
    faction,
    route: [...route],
    hops: [...(fact.hops ?? [])],
    anomalies: { ...(fact.anomalies ?? {}) },
  };
}

/** Systems to highlight while the action replays. */
export function livePositions(move: LiveMove, data: GameData | undefined): string[] {
  if (move.kind === "move") return move.route;
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
  return (
    unitsAt(after, move.faction, source, anywhere) <
      unitsAt(before, move.faction, source, anywhere) &&
    unitsAt(after, move.faction, target, inSpace) >
      unitsAt(before, move.faction, target, inSpace)
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
  if (liveAtArrival && live !== liveAtArrival) {
    return moveLanded(liveAtArrival, live, move) ? liveAtArrival : undefined;
  }
  if (previousAtArrival && moveLanded(previousAtArrival, live, move)) return previousAtArrival;
  return undefined;
}
