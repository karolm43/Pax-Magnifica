/**
 * First-time milestone tips (Layer 3) - PURE detection from the coach context. Each tip is shown
 * once (just in time, when its moment first comes up) and remembered via `markTipSeen`.
 */
import type { CoachContext } from "./coachHint";
import { TUTORIAL_TARGETS, type TutorialTargetId } from "./targets";
import type { MilestoneId } from "./tutorialStore";

export type MilestoneTip = {
  id: MilestoneId;
  title: string;
  lines: string[];
  /** Screen region "Show me" pulses. */
  targetId: TutorialTargetId;
};

export const MILESTONE_TIPS: Record<MilestoneId, MilestoneTip> = {
  "strategy-pick": {
    id: "strategy-pick",
    title: "Your first Strategy Card",
    lines: [
      "Pick a card on the Strategy Card table. Its number is your initiative: lower numbers act first in the action phase.",
    ],
    targetId: TUTORIAL_TARGETS.strategyCards,
  },
  "tactical-activation": {
    id: "tactical-activation",
    title: "Your first tactical action",
    lines: [
      "Activate a system: it takes a command token from your tactic pool.",
      "Then move ships in from adjacent systems; ships that are in a system with your command token cannot move out.",
    ],
    targetId: TUTORIAL_TARGETS.map,
  },
  secondary: {
    id: "secondary",
    title: "Follow a secondary?",
    lines: [
      "Another player played a Strategy Card. You may resolve its secondary ability, usually by spending a command token from your strategy pool, or decline.",
    ],
    targetId: TUTORIAL_TARGETS.secondaryDecision,
  },
  combat: {
    id: "combat",
    title: "Your first battle",
    lines: [
      "Each round, every unit rolls; a result equal to or above its combat value is a hit.",
      "Hits are assigned by the player who takes them. Combat ends when a side retreats or has no units left.",
    ],
    targetId: TUTORIAL_TARGETS.battle,
  },
  production: {
    id: "production",
    title: "Building units",
    lines: [
      "Units with PRODUCTION (e.g. a space dock) may build in the active system. Pay the cost by exhausting planets for their resources or by spending trade goods.",
    ],
    targetId: TUTORIAL_TARGETS.tacticalAction,
  },
};

/** Most urgent first: when two moments overlap, the one that blocks play wins. */
const PRIORITY: MilestoneId[] = ["combat", "secondary", "production", "tactical-activation", "strategy-pick"];

/** Whether the moment a tip explains is happening right now (regardless of whether it was seen). */
export function milestoneActive(id: MilestoneId, c: CoachContext): boolean {
  if (c.winner || c.setupPending) return false;
  switch (id) {
    case "combat":
      return c.inCombat;
    case "secondary":
      return c.windowOpen && c.myDecision;
    case "production":
      return c.phase === "action" && c.myTurn && c.activeSystem != null && c.tacticalStep === "PRODUCTION";
    case "tactical-activation": {
      if (c.phase !== "action" || !c.myTurn || c.inCombat || c.windowOpen) return false;
      if (c.activeSystem != null) {
        const step = c.tacticalStep ?? "MOVEMENT";
        return step === "ACTIVATION" || step === "MOVEMENT";
      }
      return !c.passed && !c.tookAction;
    }
    case "strategy-pick":
      return c.phase === "strategy" && c.myTurn && !c.myCardPicked;
  }
}

/** The tip to show now: the most urgent active moment not seen yet, or null. */
export function pendingMilestone(c: CoachContext, seenTips: readonly string[]): MilestoneId | null {
  return PRIORITY.find((id) => !seenTips.includes(id) && milestoneActive(id, c)) ?? null;
}
