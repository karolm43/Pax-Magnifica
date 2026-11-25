import type { SpaceCannonPanel } from "@/api/useBoardEditor";

/** What a non-active seat has to do in the Space Cannon Offense window (or null: nothing). */
export type SpaceCannonRole = "assign" | "fire" | "wait" | "done";

/**
 * Role of ``faction`` in the open Space Cannon Offense window (RULES.md 38): covering hits of a
 * pending shot aimed at it, firing (its turn in the queue), waiting for its turn or done (fired or
 * passed, watching the rest). A seat that is neither queued nor targeted has nothing to answer -
 * null keeps the window closed.
 */
export function spaceCannonRole(
  panel: Pick<SpaceCannonPanel, "isOpen" | "queue" | "responded" | "current" | "pending">,
  faction: string,
): SpaceCannonRole | null {
  if (panel.pending?.target === faction) return "assign";
  if (!panel.isOpen || !panel.queue.includes(faction)) return null;
  if (panel.responded.includes(faction)) return "done";
  if (panel.current === faction && panel.pending === null) return "fire";
  return "wait";
}
