import type { MapUnitTransition, StateCounts } from "@/entities/replay/types";
import { flightDuration, flightPathDuration } from "@/entities/replay/flightPath";
import type { useMapFlightAnimation } from "./useMapFlightAnimation";
import classes from "../UnitStack.module.css";

type FlightOptions = Parameters<typeof useMapFlightAnimation>[0];

const TRANSITION_CLASS: Record<MapUnitTransition["kind"], string> = {
  moved: classes.mapTransitionMoved,
  settled: classes.mapTransitionMoved,
  retreated: classes.mapTransitionRetreated,
  removed: classes.mapTransitionRemoved,
  added: classes.mapTransitionAdded,
};

const MOVING_KINDS = new Set<MapUnitTransition["kind"]>([
  "moved",
  "retreated",
  "settled",
]);

function sourceHoldClass(transition: MapUnitTransition): string {
  if (transition.hideAfterMs !== undefined) {
    return classes.mapTransitionSourcePreHold;
  }
  return transition.appearAtMs !== undefined
    ? classes.mapTransitionSourceHoldDelayed
    : classes.mapTransitionSourceHold;
}

function getTransitionClass(transition: MapUnitTransition): string {
  if (transition.badgeCountChange) return classes.mapTransitionBadgeCount;
  if (transition.sourceHold) return sourceHoldClass(transition);
  if (transition.residualAsset && transition.kind === "removed") {
    return classes.mapTransitionResidualRemoved;
  }
  return TRANSITION_CLASS[transition.kind];
}

export function transitionClassName(transition?: MapUnitTransition): string {
  if (!transition) return "";
  return `${classes.mapTransition} ${getTransitionClass(transition)}`;
}

/** How long this transition's own flight lasts (drives the engine glow). */
function ownFlightMs(transition: MapUnitTransition): number {
  const { stack } = transition;
  return transition.flightPath
    ? flightPathDuration({ x: stack.x, y: stack.y }, transition.flightPath)
    : flightDuration(transition.toX - stack.x, transition.toY - stack.y);
}

/** Ships that visibly fly (engines lit): moving kinds, not cargo riding inside a carrier. */
export function isVisibleFlight(transition?: MapUnitTransition): boolean {
  return (
    !!transition &&
    MOVING_KINDS.has(transition.kind) &&
    !transition.hiddenInFlight &&
    !transition.sourceHold
  );
}

export function transitionDelayStyle(
  transition?: MapUnitTransition,
): React.CSSProperties | undefined {
  if (!transition) return undefined;
  return {
    "--map-flight-duration": `${ownFlightMs(transition)}ms`,
    "--map-transition-delay": `${transition.delayMs ?? 0}ms`,
    "--map-appear-delay": `${transition.appearAtMs ?? 0}ms`,
    "--map-start-rotation": `${transition.startRotationDeg ?? 0}deg`,
  } as React.CSSProperties;
}

/** Ships rotate along their trajectory; other entities only translate. */
export function flightOptions(
  transition: MapUnitTransition | undefined,
  x: number,
  y: number,
  rotate: boolean,
): FlightOptions {
  const rotation = (deg: number | undefined) => (rotate ? deg : undefined);
  const continuation = transition?.continuation;
  return {
    enabled: !!transition && MOVING_KINDS.has(transition.kind),
    deltaX: transition ? transition.toX - x : 0,
    deltaY: transition ? transition.toY - y : 0,
    rotateToTrajectory: rotate,
    delayMs: transition?.delayMs ?? 0,
    holdFromMs: transition?.holdFromMs,
    hideAfterMs: transition?.hideAfterMs,
    startRotationDeg: rotation(transition?.startRotationDeg),
    holdRotationDeg: rotation(transition?.holdRotationDeg),
    parkRotationDeg: rotation(transition?.parkRotationDeg),
    // Waypoints relative to the element's own origin (the flight translates from 0,0).
    path: transition?.flightPath?.map((leg) => ({ ...leg, x: leg.x - x, y: leg.y - y })),
    hiddenInFlight: transition?.hiddenInFlight,
    continuation: continuation
      ? {
          deltaX: continuation.toX - x,
          deltaY: continuation.toY - y,
          delayMs: continuation.delayMs,
          startRotationDeg: rotation(continuation.startRotationDeg),
          parkRotationDeg: rotation(continuation.parkRotationDeg),
        }
      : undefined,
  };
}

export type UnitSlot = {
  index: number;
  galvanized: boolean;
  sustained: boolean;
  delayDamage: boolean;
};

function range(length: number): number[] {
  return Array.from({ length }, (_, i) => i);
}

/**
 * Orders a stack's units into layout slots: galvanized-sustained first, then
 * galvanized, then sustained, then plain. Slot indices follow the layout
 * states (which may differ from the live states mid-replay) plus any replay
 * offsets, with one extra gap after a multi-unit galvanized group.
 */
export function unitSlots({
  states,
  layoutStates,
  layoutOffsets,
  delayedDamage,
  showIndividualGalvanized,
}: {
  states: StateCounts;
  layoutStates: StateCounts;
  layoutOffsets: StateCounts;
  delayedDamage: StateCounts;
  showIndividualGalvanized: boolean;
}): UnitSlot[] {
  const [plain, sustained, galvanized, galvanizedSustained] = states;
  const galvanizeGap = layoutStates[2] + layoutStates[3] > 1 ? 1 : 0;
  const galvanizedStart = layoutStates[3];
  const sustainedStart = galvanizedStart + layoutStates[2] + galvanizeGap;
  const plainStart = sustainedStart + layoutStates[1];

  return [
    ...range(galvanizedSustained).map((i) => ({
      index: layoutOffsets[3] + i,
      galvanized: showIndividualGalvanized,
      sustained: true,
      delayDamage: i >= galvanizedSustained - delayedDamage[3],
    })),
    ...range(galvanized).map((i) => ({
      index: galvanizedStart + layoutOffsets[2] + i,
      galvanized: showIndividualGalvanized,
      sustained: false,
      delayDamage: false,
    })),
    ...range(sustained).map((i) => ({
      index: sustainedStart + layoutOffsets[1] + i,
      galvanized: false,
      sustained: true,
      delayDamage: i >= sustained - delayedDamage[1],
    })),
    ...range(plain).map((i) => ({
      index: plainStart + layoutOffsets[0] + i,
      galvanized: false,
      sustained: false,
      delayDamage: false,
    })),
  ];
}
