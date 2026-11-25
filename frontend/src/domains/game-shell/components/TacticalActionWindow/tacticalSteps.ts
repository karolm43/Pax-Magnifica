/**
 * Guided tactical action (RULES.md 19): step metadata, step statuses, the plain-English prompt
 * of the current step, the window's single primary action and the rule lock that blocks it.
 * Pure functions - the window component only wires them to game state.
 */

export type TacticalStepId =
  | "MOVEMENT"
  | "SPACE_CANNON"
  | "SPACE_COMBAT"
  | "INVASION"
  | "PRODUCTION";

export const TACTICAL_STEPS: { step: TacticalStepId; label: string }[] = [
  { step: "MOVEMENT", label: "Move ships" },
  { step: "SPACE_CANNON", label: "Space Cannon" },
  { step: "SPACE_COMBAT", label: "Space combat" },
  { step: "INVASION", label: "Invasion" },
  { step: "PRODUCTION", label: "Production" },
];

export type StepStatus = "done" | "active" | "skipped" | "upcoming";

export const STATUS_LABEL: Record<StepStatus, string> = {
  done: "Done",
  active: "Active",
  skipped: "Skipped",
  upcoming: "Upcoming",
};

export function stepIndex(step: string | null): number {
  return TACTICAL_STEPS.findIndex((s) => s.step === step);
}

/**
 * Status of every step: before the current one it is "done" when the window saw it during this
 * action, otherwise "skipped" (the engine skips steps with nothing to resolve). Steps before
 * the first one the window saw (opened mid-action) are unknown and count as done.
 */
export function stepStatuses(
  current: string | null,
  visited: readonly string[],
): Record<TacticalStepId, StepStatus> {
  const now = stepIndex(current);
  const seen = visited.map(stepIndex).filter((i) => i >= 0);
  const first = seen.length > 0 ? Math.min(...seen) : now;
  return Object.fromEntries(
    TACTICAL_STEPS.map(({ step }, index) => [
      step,
      index === now
        ? "active"
        : index > now
          ? "upcoming"
          : index < first || visited.includes(step)
            ? "done"
            : "skipped",
    ]),
  ) as Record<TacticalStepId, StepStatus>;
}

/** What the window knows about the current situation (from game state + the flight plan). */
export type StepContext = {
  system: string;
  /** Ships already moved in this action. */
  moved: boolean;
  /** Ships staged in the flight plan / systems they fly from. */
  stagedShips: number;
  stagedCargo: number;
  stagedSystems: number;
  /** Why the plan cannot fly yet. */
  flightBlocker: string | null;
  /** Open timing window type (`SPACE_CANNON`, `CAPACITY`, `FLEET_POOL`, `REACTION`...). */
  windowType: string | null;
  inCombat: boolean;
  /** Two players have ships in the active system (space combat is mandatory). */
  combatOwed: boolean;
  /** An invasion is running and not yet at Establish Control. */
  invasionOpen: boolean;
  invasionResolved: boolean;
};

/** One-line plain-English prompt of the current step. */
export function stepPrompt(step: string | null, ctx: StepContext): string {
  switch (step) {
    case "MOVEMENT":
      if (ctx.stagedShips + ctx.stagedCargo > 0) {
        return `Add ships from more glowing systems, or fly the plan into ${ctx.system}.`;
      }
      return ctx.moved
        ? "Your fleet has arrived. Go on to the next step."
        : `Click a glowing system on the map to pick ships that fly into ${ctx.system}. Nothing moves until you fly.`;
    case "SPACE_CANNON":
      return ctx.windowType === "SPACE_CANNON"
        ? "Players with Space Cannon in range may fire at the ships that just arrived."
        : "Space Cannon is resolved. Go on to the next step.";
    case "SPACE_COMBAT":
      if (ctx.inCombat) return "Space combat is on - resolve it in the battle window.";
      return ctx.combatOwed
        ? "Two fleets share this system - the space combat must be fought."
        : "No opposing fleet here. Go on to the next step.";
    case "INVASION":
      if (ctx.inCombat) return "Ground combat is on - resolve it in the battle window.";
      if (ctx.invasionResolved) return "Invasion resolved. Go on to the next step.";
      return ctx.invasionOpen
        ? "Bombard, then land ground forces on planets - or skip the invasion."
        : "Nothing to land here. Go on to the next step.";
    case "PRODUCTION":
      return "Build units with the PRODUCTION of your units in this system, then finish the action.";
    default:
      return "";
  }
}

/** Rule lock above the primary button, phrased as what to do about it (null = free). */
export function lockReason(ctx: StepContext, step: string | null): string | null {
  if (ctx.inCombat) return "A combat is in progress - finish it in the battle window.";
  switch (ctx.windowType) {
    case "SPACE_CANNON":
      return "Space Cannon is being resolved - wait until every player has fired or passed.";
    case "CAPACITY":
      return "Units exceed capacity - choose the excess to remove in the capacity window.";
    case "FLEET_POOL":
      return "Ships exceed the fleet pool - choose the ships to remove in the fleet pool window.";
    case "REACTION":
      return "Players are still deciding on their abilities - wait for their answers.";
    default:
      break;
  }
  if (ctx.invasionOpen) return "The invasion is in progress - finish or skip it first.";
  if (step === "SPACE_COMBAT" && ctx.combatOwed) {
    return "Space combat is mandatory - start it first.";
  }
  return null;
}

export type PrimaryKind = "fly" | "next" | "finish" | "battle" | "startCombat";

export type PrimaryAction = {
  kind: PrimaryKind;
  label: string;
  /** Why it is disabled (null = enabled). */
  disabled: string | null;
};

/** The single, context-aware primary action of the window footer. */
export function primaryAction(step: string | null, ctx: StepContext): PrimaryAction {
  const isLast = step === "PRODUCTION";
  const lock = lockReason(ctx, step);
  if (step === "MOVEMENT" && ctx.stagedShips + ctx.stagedCargo > 0) {
    const ships = ctx.stagedShips;
    const label =
      `Fly ${ships} ship${ships === 1 ? "" : "s"}` +
      (ctx.stagedCargo > 0 ? ` + ${ctx.stagedCargo} cargo` : "") +
      ` from ${ctx.stagedSystems} system${ctx.stagedSystems === 1 ? "" : "s"}`;
    return { kind: "fly", label, disabled: ctx.flightBlocker ?? lock };
  }
  if (ctx.inCombat) return { kind: "battle", label: "Return to battle", disabled: null };
  if (step === "SPACE_COMBAT" && ctx.combatOwed) {
    // Normally started on step entry (RULES.md 19.1); by hand only when an open window held it.
    return { kind: "startCombat", label: "Start space combat", disabled: lockReason(ctx, null) };
  }
  if (step === "MOVEMENT" && !ctx.moved) {
    return { kind: "next", label: "No movement - next step", disabled: lock };
  }
  return isLast
    ? { kind: "finish", label: "Finish action", disabled: lock }
    : { kind: "next", label: "Next step", disabled: lock };
}
