import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { fetchJson } from "@/api/fetchJson";

/*
 * God-Mode: edycja planszy bez sprawdzania zasad. Operator (gracz) może dodawać,
 * usuwać i przesuwać jednostki dowolnie. Endpointy w korzeniu backendu (proxy /bot).
 */
const BOT_ROOT = "/bot";

async function post(path: string, body: unknown): Promise<void> {
  const response = await fetch(`${BOT_ROOT}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`God-Mode edit failed (${response.status}). ${detail}`.trim());
  }
}

export type EditUnitArgs = {
  position: string;
  zone: string; // "space" albo ID planety
  faction: string;
  asyncId: string;
  delta: number;
};

export type MoveUnitArgs = {
  fromPosition: string;
  fromZone: string;
  toPosition: string;
  toZone: string;
  faction: string;
  asyncId: string;
  count?: number;
};

/** Edytowalne pola gracza (God-Mode). Wszystkie opcjonalne — podane nadpisują. */
export type PlayerEdit = {
  faction?: string;
  color?: string;
  victory_points?: number;
  trade_goods?: number;
  commodities?: number;
  tactical_cc?: number;
  fleet_cc?: number;
  strategic_cc?: number;
  cc_reinf?: number;
  passed?: boolean;
  strategy_cards?: number[];
  controlled_planets?: string[];
  technologies?: string[];
  leader_states?: Record<string, string>;
};

/**
 * Hook z akcjami edycji planszy (God-Mode). Każda akcja po sukcesie inwaliduje
 * dokument web-data, więc plansza i panele odświeżają się natychmiast.
 */
export function useBoardEditor() {
  const queryClient = useQueryClient();

  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ["playerData"] });
    await queryClient.invalidateQueries({ queryKey: ["history"] });
    await queryClient.invalidateQueries({ queryKey: ["strategyCards"] });
  }, [queryClient]);

  const editUnit = useCallback(
    async ({ position, zone, faction, asyncId, delta }: EditUnitArgs) => {
      await post(`/system/${position}/edit-units`, {
        zone,
        faction,
        asyncId,
        delta,
      });
      await refresh();
    },
    [refresh],
  );

  const moveUnit = useCallback(
    async (args: MoveUnitArgs) => {
      await post("/units/move", {
        fromPosition: args.fromPosition,
        fromZone: args.fromZone,
        toPosition: args.toPosition,
        toZone: args.toZone,
        faction: args.faction,
        asyncId: args.asyncId,
        count: args.count ?? 1,
      });
      await refresh();
    },
    [refresh],
  );

  const undo = useCallback(async () => {
    await post("/undo", {});
    await refresh();
  }, [refresh]);

  const redo = useCallback(async () => {
    await post("/redo", {});
    await refresh();
  }, [refresh]);

  const gotoHistory = useCallback(
    async (seq: number) => {
      await post(`/history/goto/${seq}`, {});
      await refresh();
    },
    [refresh],
  );

  const editPlayer = useCallback(
    async (playerId: string, edit: PlayerEdit) => {
      await post(`/player/${playerId}/edit`, edit);
      await refresh();
    },
    [refresh],
  );

  const endTurn = useCallback(async () => {
    await post("/turn/end", {});
    await refresh();
  }, [refresh]);

  const passTurn = useCallback(async () => {
    await post("/turn/pass", {});
    await refresh();
  }, [refresh]);

  const nextPhase = useCallback(async () => {
    await post("/phase/next", {});
    await refresh();
  }, [refresh]);

  const nextRound = useCallback(async () => {
    await post("/round/next", {});
    await refresh();
  }, [refresh]);

  const pickStrategyCard = useCallback(
    async (playerId: string, initiative: number) => {
      await post("/strategy/pick", {
        player_id: playerId,
        initiative,
      });
      await refresh();
    },
    [refresh],
  );

  const playStrategyCard = useCallback(
    async (playerId: string, initiative: number) => {
      await post("/strategy/play", {
        player_id: playerId,
        initiative,
      });
      await refresh();
    },
    [refresh],
  );

  // --- Akcja taktyczna (E3) ---

  const activateSystem = useCallback(
    async (position: string) => {
      await post("/tactical/activate", { position });
      await refresh();
    },
    [refresh],
  );

  const tacticalNextStep = useCallback(async () => {
    await post("/tactical/step/next", {});
    await refresh();
  }, [refresh]);

  const tacticalSetStep = useCallback(
    async (step: string) => {
      await post("/tactical/step/set", { step });
      await refresh();
    },
    [refresh],
  );

  const endTactical = useCallback(async () => {
    await post("/tactical/end", {});
    await refresh();
  }, [refresh]);

  const placeCommandToken = useCallback(
    async (position: string, faction: string) => {
      await post(`/system/${position}/command-token`, { faction });
      await refresh();
    },
    [refresh],
  );

  return {
    editUnit,
    moveUnit,
    undo,
    redo,
    gotoHistory,
    editPlayer,
    endTurn,
    passTurn,
    nextPhase,
    nextRound,
    pickStrategyCard,
    playStrategyCard,
    activateSystem,
    tacticalNextStep,
    tacticalSetStep,
    endTactical,
    placeCommandToken,
  };
}

export type StrategyCardState = {
  initiative: number;
  id: string;
  name: string;
  primary_texts: string[];
  secondary_texts: string[];
  colour_hex_code: string | null;
  trade_goods: number;
  picked_by: string | null;
  exhausted: boolean;
};

/** Pula kart strategii aktywnego zestawu + ich stan w bieżącej grze. */
export function useStrategyCards() {
  return useQuery<StrategyCardState[]>({
    queryKey: ["strategyCards"],
    queryFn: async () =>
      fetchJson<StrategyCardState[]>("/bot/strategy/cards", "strategyCards"),
    staleTime: 0,
  });
}

export type HistoryEntry = { seq: number; label: string; is_current: boolean };

/** Lista migawek historii (Event Sourcing) do panelu historii. */
export function useHistory() {
  return useQuery<HistoryEntry[]>({
    queryKey: ["history"],
    queryFn: async () => {
      const data = await fetchJson<{ entries: HistoryEntry[] }>(
        "/bot/history",
        "history",
      );
      return data.entries;
    },
    // Odświeżaj przy każdym wejściu — po edycjach historia się zmienia.
    staleTime: 0,
  });
}
