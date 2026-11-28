import { TUTORIAL_TARGETS, type TutorialTargetId } from "./targets";

/** One stop of the Guided UI Tour (Layer 2). */
export type TourStep = {
  id: string;
  /** Region to spotlight; with a list, the first one on screen wins (fallbacks in order). */
  target: TutorialTargetId | TutorialTargetId[];
  title: string;
  body: string;
};

/** Resolves a target id to its visible element, or null (injected so helpers stay testable). */
export type TargetFinder = (id: TutorialTargetId) => HTMLElement | null;

export const TOUR_STEPS: TourStep[] = [
  {
    id: "map",
    target: TUTORIAL_TARGETS.map,
    title: "The galaxy",
    body:
      "This is the board. Drag to pan, scroll to zoom. Your home system is where your fleet starts; " +
      "Mecatol Rex sits in the centre. Whenever the game needs a system or planet from you, the valid " +
      "targets light up here — just click one.",
  },
  {
    id: "phase",
    target: [TUTORIAL_TARGETS.coach, TUTORIAL_TARGETS.phasePanel],
    title: "What now?",
    body:
      "The phase panel shows the round, the current phase and whose turn it is. Its \"What now?\" section " +
      "tells you in one line what you can do at this moment — check it whenever you are unsure.",
  },
  {
    id: "economy",
    target: [TUTORIAL_TARGETS.commandPools, TUTORIAL_TARGETS.economy],
    title: "Command tokens & economy",
    body:
      "Command tokens are your actions. Tactic pool: spend one to activate a system. Fleet pool: how many " +
      "non-fighter ships may share a system. Strategy pool: spend one to follow another player's strategy " +
      "card. Next to them are your resources, influence, trade goods and commodities.",
  },
  {
    id: "turn",
    target: TUTORIAL_TARGETS.turnControls,
    title: "Your turn",
    body:
      "On your turn, act from here: play your strategy card, take a component action, end your turn, or " +
      "pass when you have nothing more to do this round. Activating a system is done on the map.",
  },
  {
    id: "strategy",
    target: TUTORIAL_TARGETS.strategyCards,
    title: "Strategy cards",
    body:
      "In the strategy phase each player picks a strategy card, starting with the speaker. The number on " +
      "the card is its initiative: lower numbers act first in the action phase. Unpicked cards gain a " +
      "trade good each round.",
  },
  {
    id: "hand",
    target: TUTORIAL_TARGETS.hand,
    title: "Your hand",
    body:
      "Action cards, secret objectives and promissory notes live here. To play an action card, drag it " +
      "out of your hand — only cards you can legally play right now can be picked up.",
  },
  {
    id: "toolbar",
    target: [TUTORIAL_TARGETS.mapLenses, TUTORIAL_TARGETS.mapToolbar],
    title: "Map lenses & log",
    body:
      "Lenses add information on top of the map: planet traits, technology skips, Space Cannon range and " +
      "more. The event log lists everything that has happened, and the help buttons open the guide or " +
      "replay this tour.",
  },
  {
    id: "objectives",
    target: [TUTORIAL_TARGETS.objectives, TUTORIAL_TARGETS.boardHud],
    title: "Objectives & players",
    body:
      "Below the board: the victory point track, public objectives you can score in the status phase, " +
      "laws in play and every player's area. The first player to reach the target score wins.",
  },
];

function targetsOf(step: TourStep): TutorialTargetId[] {
  return Array.isArray(step.target) ? step.target : [step.target];
}

/** The first visible element among the step's targets (fallbacks in order), or null. */
export function resolveStep(step: TourStep, find: TargetFinder): HTMLElement | null {
  for (const id of targetsOf(step)) {
    const el = find(id);
    if (el) return el;
  }
  return null;
}

/**
 * The next step index from `from` in direction `dir` (exclusive) whose target is on screen;
 * null when there is none before the end (or the start). Steps whose regions are all
 * unmounted (another phase, a mobile layout) are skipped.
 */
export function nextAvailableStep(
  steps: TourStep[],
  from: number,
  dir: 1 | -1,
  find: TargetFinder,
): number | null {
  for (let i = from + dir; i >= 0 && i < steps.length; i += dir) {
    if (resolveStep(steps[i], find)) return i;
  }
  return null;
}
