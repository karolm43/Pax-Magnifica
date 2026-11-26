import { useCallback } from "react";
import { fetchJson } from "@/api/fetchJson";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import {
  BOOST_NAMES,
  boostConflicts,
  draftAsLeg,
  flightBatches,
  legCargoCount,
  legRequest,
  legShipCount,
  needsSeparateOrder,
  planIncoming,
  replannedLeg,
  type IncomingFleet,
  type SeparateOrder,
  type StagedLeg,
} from "./flightPlan";
import type { MoveRouteData } from "./routeTypes";

/** Fresh route preview of a leg (its source + waypoints) on the board as it is NOW. */
async function freshRoute(leg: StagedLeg): Promise<MoveRouteData> {
  return fetchJson<MoveRouteData>(
    `/bot/tactical/move-route?faction=${encodeURIComponent(leg.faction)}&from_position=${encodeURIComponent(leg.from)}&via=${encodeURIComponent(leg.via.join(","))}`,
    "moveRoute",
  );
}

export type FlightPlanState = {
  /** Legs that "Fly" sends: staged legs + the leg open in the editor (when complete). */
  legs: StagedLeg[];
  ships: number;
  cargo: number;
  systems: number;
  incoming: IncomingFleet;
  /** Why the plan cannot fly yet (null = ready, or nothing staged). */
  blocker: string | null;
  /** The plan holds a ship that may move before or after the others (Hil Colish) + other legs. */
  separateOrderAsked: boolean;
  separateOrder: SeparateOrder;
  setSeparateOrder: (order: SeparateOrder) => void;
  fly: () => Promise<void>;
  discard: () => void;
};

/**
 * Flight plan of the Move Ships step (RULES.md 32.4) as the tactical window uses it: legs to
 * send, combined numbers for the preview, and ``fly`` = one ``/tactical/move-batch``. The leg
 * open in the editor is flown too, so "Fly" never silently drops what the player just picked.
 */
export function useFlightPlan(): FlightPlanState {
  const plan = useAppStore((s) => s.movePlan);
  const draft = useAppStore((s) => s.moveDraft);
  const clearMovePlan = useAppStore((s) => s.clearMovePlan);
  const closeMoveDraft = useAppStore((s) => s.closeMoveDraft);
  const separateOrder = useAppStore((s) => s.separateMoveOrder);
  const setSeparateOrder = useAppStore((s) => s.setSeparateMoveOrder);
  const removeStagedLeg = useAppStore((s) => s.removeStagedLeg);
  const setNotice = useAppStore((s) => s.setNotice);
  const { moveBatch } = useBoardEditor();

  // The open leg joins the plan when it is complete; Ion Storm needs the explicit choice made
  // in the editor, so such a leg has to be added there first.
  const openLeg =
    draft && !draft.route?.ionStormChoice ? draftAsLeg(draft, draft.legId ?? "open") : null;
  const legs = openLeg
    ? [...plan.filter((l) => l.id !== openLeg.id), openLeg]
    : plan;
  const openUnstaged =
    draft !== null &&
    openLeg === null &&
    legShipCount(draft.picks) + legCargoCount(draft.picks) > 0;

  const conflicts = boostConflicts(legs);
  const blocker = openUnstaged
    ? "Add the leg you are editing to the flight plan (or close it) first."
    : conflicts.length > 0
      ? `${BOOST_NAMES[conflicts[0].boost]} extends only ONE ship per action - legs from ${conflicts[0].froms.join(" and ")} both need it.`
      : null;

  const faction = legs[0]?.faction ?? null;
  const fly = useCallback(async () => {
    if (!faction || legs.length === 0 || blocker) return;
    try {
      // Hil Colish before / after the other ships: one or two flights in that order.
      const batches = flightBatches(legs, separateOrder);
      for (const [index, planned] of batches.entries()) {
        // A later flight re-plans its legs on the board the earlier one left (the routes were
        // previewed with Hil Colish where it started); the player's waypoints are kept.
        let batch = planned;
        if (index > 0) {
          const replanned = await Promise.all(
            planned.map(async (leg) => replannedLeg(leg, await freshRoute(leg))),
          );
          const problem = replanned.find((r): r is string => typeof r === "string");
          if (problem) {
            setNotice(problem, "error");
            return;
          }
          batch = replanned as StagedLeg[];
        }
        await moveBatch(faction, batch.map(legRequest));
        // Flown legs leave the plan, so a failing later flight keeps only what is left.
        batch.forEach((leg) => removeStagedLeg(leg.id));
        if (openLeg && batch.some((leg) => leg.id === openLeg.id)) closeMoveDraft();
      }
      clearMovePlan();
      closeMoveDraft();
    } catch {
      // The reason (422, naming the leg) is shown by the notice panel; the plan stays to fix.
    }
  }, [faction, legs, openLeg, blocker, separateOrder, moveBatch, removeStagedLeg, setNotice, clearMovePlan, closeMoveDraft]);

  const discard = useCallback(() => {
    clearMovePlan();
    closeMoveDraft();
  }, [clearMovePlan, closeMoveDraft]);

  return {
    legs,
    ships: legs.reduce((n, l) => n + legShipCount(l.picks), 0),
    cargo: legs.reduce((n, l) => n + legCargoCount(l.picks), 0),
    systems: new Set(legs.map((l) => l.from)).size,
    incoming: planIncoming(legs),
    blocker,
    separateOrderAsked: needsSeparateOrder(legs),
    separateOrder,
    setSeparateOrder,
    fly,
    discard,
  };
}
