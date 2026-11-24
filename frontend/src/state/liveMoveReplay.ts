import type { ActivityEntry, ActivityPlayer } from "@/api/boardQueries";
import type { GameData } from "@/entities/game/types";
import type { LiveMove } from "@/entities/replay/types";
import { allUnitStacks, stackHolder, stateCount, unitStates } from "@/entities/replay/unitState";

/**
 * Live fleet-move replay: every client turns a new Activity `tactical.move` entry carrying a
 * `move_route` fact into the same physical flight on its own map. Pure helpers live here;
 * `useLiveMoveReplay` pairs the entry with the map data before and after the move.
 */

/** The move an Activity entry announces, or undefined when it is not a routed fleet move. */
export function liveMoveFromEntry(
  entry: ActivityEntry,
  players: Record<string, ActivityPlayer>,
): LiveMove | undefined {
  const activity = entry.activity;
  if (activity.action !== "tactical.move" || !activity.actor_id) return undefined;
  const fact = activity.facts.find((f) => f.type === "move_route");
  const route = fact?.route;
  if (!route || route.length < 2) return undefined;
  const faction = players[activity.actor_id]?.faction;
  if (!faction) return undefined;
  return {
    faction,
    route: [...route],
    hops: [...(fact.hops ?? [])],
    anomalies: { ...(fact.anomalies ?? {}) },
  };
}

function unitsAt(data: GameData, faction: string, position: string, space: boolean): number {
  return allUnitStacks(data)
    .filter(
      (located) =>
        located.position === position &&
        located.stack.faction === faction &&
        (stackHolder(located.stack) === "space") === space,
    )
    .reduce((total, located) => total + stateCount(unitStates(located.stack)), 0);
}

/**
 * Whether `before` -> `after` is exactly this move: the faction lost units in the route's
 * source system and gained units in the destination's space. Guards against pairing the
 * entry with an unrelated refresh (e.g. an earlier move into the same active system).
 */
export function moveLanded(before: GameData, after: GameData, move: LiveMove): boolean {
  const source = move.route[0];
  const target = move.route[move.route.length - 1];
  const leftSource =
    unitsAt(after, move.faction, source, true) + unitsAt(after, move.faction, source, false) <
    unitsAt(before, move.faction, source, true) + unitsAt(before, move.faction, source, false);
  return leftSource && unitsAt(after, move.faction, target, true) > unitsAt(before, move.faction, target, true);
}

export type PendingLiveMove = {
  move: LiveMove;
  /** Live map when the entry arrived, and the one before it. */
  liveAtArrival: GameData | undefined;
  previousAtArrival: GameData | undefined;
};

/**
 * The map state before the move, once the live map shows it - or undefined to keep waiting.
 * The feed and the map refresh separately after a push, in either order.
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
