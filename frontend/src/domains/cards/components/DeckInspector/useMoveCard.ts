import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "@/state/appStore";

/** Stos docelowy: `top` = wierzch talii (ustawia „następną" kartę), `deck` = w losowe miejsce. */
export type MoveTarget = "top" | "deck" | "discard" | "purged";

/**
 * Debug: przenosi kartę między talią / odrzuconymi / purge (`POST /decks/move`). Silnik omija
 * reguły (God-Mode); 422 z powodem trafia do panelu komunikatów.
 */
export function useMoveCard() {
  const queryClient = useQueryClient();
  return useCallback(
    async (cardId: string, to: MoveTarget) => {
      const response = await fetch("/bot/decks/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cardId, to }),
      });
      if (!response.ok) {
        const raw = await response.text().catch(() => "");
        let message = raw || `Error ${response.status}`;
        try {
          const parsed = JSON.parse(raw) as { detail?: unknown };
          if (typeof parsed.detail === "string") message = parsed.detail;
        } catch {
          // nie-JSON - zostaje surowy tekst
        }
        useAppStore.getState().setNotice(message, "error");
        return;
      }
      for (const key of ["playerData", "history", "exploration"]) {
        void queryClient.invalidateQueries({ queryKey: [key] });
      }
    },
    [queryClient],
  );
}
