import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import { useAppStore } from "@/state/appStore";

/*
 * Moduł Thunder's Edge (RULES.md 50): ekspedycje, The Fracture, Thunder's Edge. Odczyt stanu
 * (`GET /thunders-edge`) i akcje. Reguły WALIDUJE silnik (422 z powodem → panel komunikatów),
 * UI tylko prowadzi gracza.
 */
const BOT_ROOT = "/bot";

/** Plastry żetonu ekspedycji (kolejność zegarowa od góry, jak w backendzie). */
export type SliceId =
  | "fiveRes"
  | "actionCards"
  | "fiveInf"
  | "secret"
  | "techSkip"
  | "tradeGoods";

export type ThundersEdgeView = {
  slices: { id: SliceId; claimedBy: string | null }[];
  freeSlices: SliceId[];
  canPerform: boolean;
  blockReason: string;
  fractureInPlay: boolean;
  fractureEnteredBy: string | null;
  lastRoll: { playerId: string; result: number; success: boolean; seq: number } | null;
  pendingIngress: { color: string; remaining: number; candidates: string[] }[];
  placementPlayer: string | null;
  placementTargets: string[];
  placementCounts: Record<string, number>;
  placementLeaders: string[];
  thundersEdgePosition: string | null;
  payment: {
    resources: Record<string, number>;
    influence: Record<string, number>;
    tradeGoods: number;
    specialtyPlanets: string[];
  };
  /** ID silnika gracza → klucz tożsamości z web-data (faction/kolor). */
  players: Record<string, string>;
  log: Record<string, unknown>[];
};

export type SlicePayment = {
  planets?: string[];
  trade_goods?: number;
  action_cards?: string[];
  secret?: string | null;
  tech_planet?: string | null;
};

/** Stan modułu; `enabled` = Thunder's Edge jest w grze (ekspedycje w web-data). */
export function useThundersEdge(enabled: boolean) {
  return useQuery<ThundersEdgeView>({
    queryKey: ["thundersEdge"],
    enabled,
    queryFn: async () =>
      fetchJson<ThundersEdgeView>("/bot/thunders-edge", "thunders-edge"),
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

/** Akcje modułu; po sukcesie oznaczają zapytania jako nieświeże. */
export function useThundersEdgeActions() {
  const queryClient = useQueryClient();
  const refresh = useCallback(() => {
    for (const key of [
      "thundersEdge",
      "playerData",
      "history",
      "playerHand",
      "production",
    ]) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  }, [queryClient]);

  const perform = useCallback(
    async (slice: SliceId, payment: SlicePayment) => {
      await post("/expeditions/perform", { slice, payment });
      refresh();
    },
    [refresh],
  );

  const placeIngress = useCallback(
    async (color: string, position: string) => {
      await post("/fracture/ingress", { color, position });
      refresh();
    },
    [refresh],
  );

  const placeThundersEdge = useCallback(
    async (position: string, infantryPlayerId?: string) => {
      await post("/thunders-edge/place", {
        position,
        infantry_player_id: infantryPlayerId ?? null,
      });
      refresh();
    },
    [refresh],
  );

  return { perform, placeIngress, placeThundersEdge };
}
