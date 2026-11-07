import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import { useAppStore } from "@/state/appStore";

/*
 * Okno EKSPLORACJI (RULES.md 46): odczyt stanu (`GET /exploration`) i akcje. Akcje WALIDUJE
 * silnik (422 z powodem → panel komunikatów), okno tylko prowadzi.
 */
const BOT_ROOT = "/bot";

export type ExploreDeck = "cultural" | "hazardous" | "industrial";

export type ExploreCard = {
  cardId: string;
  name: string;
  deck: string;
  /** Instant / Attach / Token / Fragment (z danych karty). */
  resolution: string;
  text: string;
  flavorText: string;
};

export type ExploreOption = {
  id: string;
  label: string;
  enabled: boolean;
  /** Powód niedostępności (puste, gdy opcja jest dostępna). */
  reason: string;
  /** Dodatkowy wybór (np. pula żetonu dowodzenia); puste = opcja bez parametru. */
  params: { id: string; label: string }[];
};

export type ExploreLogItem = {
  planet: string;
  deck: string;
  card: ExploreCard;
  summary: string;
  fate: "discarded" | "attached" | "kept" | "purged";
};

export type ExplorationView = {
  active: boolean;
  /** Klucz tożsamości eksplorującego gracza. */
  player: string | null;
  position: string | null;
  /** Planety czekające na eksplorację — gracz wybiera kolejność (i talię przy kilku cechach). */
  queue: { planet: string; traits: ExploreDeck[] }[];
  current: { planet: string; card: ExploreCard; options: ExploreOption[] } | null;
  log: ExploreLogItem[];
  /** Wszystko rozstrzygnięte — zostaje zamknąć okno. */
  done: boolean;
};

/** Stan okna eksploracji; `enabled` = trwa eksploracja (gameState.activeExploration). */
export function useExploration(enabled: boolean) {
  return useQuery<ExplorationView>({
    queryKey: ["exploration"],
    enabled,
    queryFn: async () =>
      fetchJson<ExplorationView>("/bot/exploration", "exploration"),
    staleTime: 0,
  });
}

async function post(path: string, body: unknown): Promise<void> {
  const response = await fetch(`${BOT_ROOT}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const raw = await response.text().catch(() => "");
    let message = raw || `Error ${response.status}`;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // nie-JSON — zostaje surowy tekst
    }
    useAppStore.getState().setNotice(message, "error");
    throw new Error(message);
  }
}

/** Akcje okna eksploracji; po sukcesie oznaczają zapytania jako nieświeże. */
export function useExplorationActions() {
  const queryClient = useQueryClient();
  const refresh = useCallback(() => {
    for (const key of [
      "exploration",
      "invasion",
      "playerData",
      "history",
      "production",
    ]) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  }, [queryClient]);

  const draw = useCallback(
    async (planet: string, deck?: ExploreDeck) => {
      await post("/exploration/draw", { planet, deck: deck ?? null });
      refresh();
    },
    [refresh],
  );

  const resolve = useCallback(
    async (option: string, param?: string) => {
      await post("/exploration/resolve", { option, param: param ?? null });
      refresh();
    },
    [refresh],
  );

  const finish = useCallback(async () => {
    await post("/exploration/finish", {});
    refresh();
  }, [refresh]);

  return { draw, resolve, finish };
}
