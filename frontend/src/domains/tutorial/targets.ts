/**
 * Tutorial target registry (Layer 1). Every HUD region the tour, the "Show me" pulse or a
 * milestone tip can point at carries a stable `data-tutorial-id` attribute with one of these ids.
 * Spread `tutorialTarget(id)` on the region's root element; resolve it with `findTutorialTarget`.
 */
export const TUTORIAL_TARGETS = {
  map: "map",
  phasePanel: "phase-panel",
  coach: "coach",
  economy: "economy",
  commandPools: "command-pools",
  turnControls: "turn-controls",
  strategyCards: "strategy-cards",
  tacticalAction: "tactical-action",
  hand: "hand",
  mapToolbar: "map-toolbar",
  mapLenses: "map-lenses",
  boardHud: "board-hud",
  objectives: "objectives",
  players: "players",
  secondaryDecision: "secondary-decision",
  battle: "battle",
  production: "production",
} as const;

export type TutorialTargetId = (typeof TUTORIAL_TARGETS)[keyof typeof TUTORIAL_TARGETS];

export const TUTORIAL_ATTR = "data-tutorial-id";

/** Props to spread on a target's root element: `<div {...tutorialTarget("hand")}>`. */
export function tutorialTarget(id: TutorialTargetId): { "data-tutorial-id": TutorialTargetId } {
  return { [TUTORIAL_ATTR]: id } as { "data-tutorial-id": TutorialTargetId };
}

/**
 * The mounted, visible element for a target, or null (unmounted, hidden, or zero-sized —
 * e.g. a desktop-only panel on mobile). Callers skip targets that resolve to null.
 */
export function findTutorialTarget(
  id: TutorialTargetId,
  root: ParentNode = document,
): HTMLElement | null {
  const nodes = root.querySelectorAll<HTMLElement>(`[${TUTORIAL_ATTR}="${id}"]`);
  for (const node of nodes) {
    const rect = node.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) return node;
  }
  return null;
}
