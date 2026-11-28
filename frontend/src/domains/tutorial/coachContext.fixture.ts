import type { CoachContext } from "./coachHint";

/** Test fixture: the viewer's own action-phase turn, Strategy Card picked, nothing else going on. */
export const BASE_COACH_CONTEXT: CoachContext = {
  phase: "action",
  setupPending: false,
  winner: false,
  turnName: "The Federation of Sol",
  myTurn: true,
  turnIsBot: false,
  myCardPicked: true,
  myCardPlayed: false,
  passed: false,
  tookAction: false,
  activeSystem: null,
  tacticalStep: null,
  inCombat: false,
  windowOpen: false,
  myDecision: false,
  isSpeaker: false,
  canAdvancePhase: false,
};
