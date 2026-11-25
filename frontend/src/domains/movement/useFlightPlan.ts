import { useCallback } from "react";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useAppStore } from "@/state/appStore";
import {
  BOOST_NAMES,
  boostConflicts,
  draftAsLeg,
  legCargoCount,
  legRequest,
  legShipCount,
  planIncoming,
  type IncomingFleet,
  type StagedLeg,
} from "./flightPlan";

export type FlightPlanState = {
  /** Legs that "Fly" sends: staged legs + the leg open in the editor (when complete). */
  legs: StagedLeg[];
  ships: number;
  cargo: number;
  systems: number;
  incoming: IncomingFleet;
  /** Why the plan cannot fly yet (null = ready, or nothing staged). */
  blocker: string | null;
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
      await moveBatch(faction, legs.map(legRequest));
      clearMovePlan();
      closeMoveDraft();
    } catch {
      // The reason (422, naming the leg) is shown by the notice panel; the plan stays to fix.
    }
  }, [faction, legs, blocker, moveBatch, clearMovePlan, closeMoveDraft]);

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
    fly,
    discard,
  };
}
