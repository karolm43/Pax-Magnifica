import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { fetchJson } from "@/api/fetchJson";
import { useAppStore } from "@/state/appStore";

/*
 * Akcje planszy. Część endpointów WALIDUJE reguły (ruch, produkcja, aktywacja,
 * flow, okna) i zwraca 422 z czytelnym powodem; część to God-Mode bez reguł
 * (edycja/przesuwanie jednostek). Odrzucenie walidacji pokazujemy graczowi jako
 * ``notice`` (baner w panelu), zamiast ciche połykać błąd.
 */
const BOT_ROOT = "/bot";

/** Wyłuskuje czytelny komunikat z odpowiedzi błędu (FastAPI: {"detail": "..."}). */
function parseDetail(raw: string, status: number): string {
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    // nie-JSON — użyj surowego tekstu niżej
  }
  return raw || `Błąd ${status}`;
}

async function post(path: string, body: unknown): Promise<void> {
  const response = await fetch(`${BOT_ROOT}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const raw = await response.text().catch(() => "");
    const message = parseDetail(raw, response.status);
    // Pokaż graczowi powód (np. „system już aktywowany", „za mało zasobów").
    useAppStore.getState().setNotice(message, "error");
    throw new Error(message);
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
  exhausted_planets?: string[];
  technologies?: string[];
  exhausted_technologies?: string[];
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
    await queryClient.invalidateQueries({ queryKey: ["combat"] });
    await queryClient.invalidateQueries({ queryKey: ["production"] });
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

  const endTurn = useCallback(
    async (playerId?: string) => {
      await post("/turn/end", { player_id: playerId ?? null });
      await refresh();
    },
    [refresh],
  );

  const passTurn = useCallback(
    async (playerId?: string) => {
      await post("/turn/pass", { player_id: playerId ?? null });
      await refresh();
    },
    [refresh],
  );

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

  const setSpeaker = useCallback(
    async (playerId: string) => {
      await post("/speaker/set", { player_id: playerId });
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

  // Ruch WALIDOWANY (RULES.md 32) — w odróżnieniu od God-Mode moveUnit (bez reguł).
  // Cel = aktywny system; backend egzekwuje zasięg/anomalie/blokady i zwraca 422,
  // gdy ruch nielegalny (wtedy post() rzuca błąd z detalem).
  const moveShips = useCallback(
    async (args: {
      fromPosition: string;
      baseType: string;
      count?: number;
      faction: string;
    }) => {
      await post("/tactical/move", {
        fromPosition: args.fromPosition,
        baseType: args.baseType,
        count: args.count ?? 1,
        faction: args.faction,
      });
      await refresh();
    },
    [refresh],
  );

  // Produkcja WALIDOWANA (RULES.md 33.2) — limit/budżet/blokada; 422 gdy nielegalna.
  // W odróżnieniu od God-Mode editUnit (bez reguł). Budżet to sprawdzenie (opcja „b").
  const produce = useCallback(
    async (
      faction: string,
      orders: { baseType: string; count: number; zone?: string }[],
    ) => {
      await post("/tactical/produce", { faction, orders });
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

  const capturePlanet = useCallback(
    async (position: string, planet: string, faction: string) => {
      await post(`/tactical/system/${position}/capture`, { planet, faction });
      await refresh();
    },
    [refresh],
  );

  // --- Kontrola komponentów (exhaust/ready planet/tech, stan liderów) ---

  const togglePlanetExhaust = useCallback(
    async (playerId: string, planetId: string) => {
      await post("/player/planet/toggle-exhaust", {
        player_id: playerId,
        component_id: planetId,
      });
      await refresh();
    },
    [refresh],
  );

  const toggleTechExhaust = useCallback(
    async (playerId: string, techId: string) => {
      await post("/player/tech/toggle-exhaust", {
        player_id: playerId,
        component_id: techId,
      });
      await refresh();
    },
    [refresh],
  );

  const setLeaderState = useCallback(
    async (playerId: string, leaderId: string, state: string) => {
      await post("/player/leader/set-state", {
        player_id: playerId,
        leader_id: leaderId,
        state,
      });
      await refresh();
    },
    [refresh],
  );

  // --- Okna czasowe (timing windows, E8-T2) ---

  const respondWindow = useCallback(
    async (playerId: string, decision?: string) => {
      await post("/window/respond", {
        player_id: playerId,
        decision: decision ?? null,
      });
      await refresh();
    },
    [refresh],
  );

  const strategySecondary = useCallback(
    async (playerId: string, execute: boolean) => {
      await post("/strategy/secondary", {
        player_id: playerId,
        execute,
      });
      await refresh();
    },
    [refresh],
  );

  const closeWindow = useCallback(async () => {
    await post("/window/close", {});
    await refresh();
  }, [refresh]);

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
    setSpeaker,
    activateSystem,
    moveShips,
    produce,
    tacticalNextStep,
    tacticalSetStep,
    endTactical,
    placeCommandToken,
    capturePlanet,
    togglePlanetExhaust,
    toggleTechExhaust,
    setLeaderState,
    respondWindow,
    strategySecondary,
    closeWindow,
  };
}

export type ProducibleUnitHelp = {
  baseType: string;
  asyncId: string;
  unitId: string;
  name: string;
  cost: number;
  unitsPerCost: number;
  /** "space" → statek (przestrzeń), "planet" → siła naziemna / struktura. */
  placement: "space" | "planet";
};

export type ProductionHelp = {
  playerId: string;
  availableResources: number;
  units: ProducibleUnitHelp[];
};

/** Pomoc liczbowa produkcji (dostępne zasoby + koszty jednostek gracza). */
export function useProductionHelp(faction: string | null) {
  return useQuery<ProductionHelp>({
    queryKey: ["production", faction],
    enabled: faction !== null,
    queryFn: async () =>
      fetchJson<ProductionHelp>(
        `/bot/tactical/production?faction=${encodeURIComponent(faction ?? "")}`,
        "production",
      ),
    staleTime: 0,
  });
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

// --- Asystent walki (E3) ---

export type CombatUnitHelp = {
  baseType: string;
  asyncId: string;
  unitId: string;
  name: string;
  count: number;
  combatHitsOn: number;
  combatDieCount: number;
  expectedHits: number;
};

export type CombatSideHelp = {
  faction: string;
  playerId: string;
  units: CombatUnitHelp[];
  totalDice: number;
  expectedHits: number;
};

export type CombatHelp = {
  position: string;
  planet: string | null;
  kind: "space" | "ground";
  sides: CombatSideHelp[];
};

/**
 * Pomoce liczbowe walki w danym miejscu (asystent — zero rzucania). ``planet``
 * ustawione → walka naziemna; brak → kosmiczna. Pusty ``sides`` = brak walki.
 */
export function useCombatHelp(position: string | null, planet: string | null) {
  return useQuery<CombatHelp>({
    queryKey: ["combat", position, planet],
    enabled: position !== null,
    queryFn: async () => {
      const q = planet ? `?planet=${encodeURIComponent(planet)}` : "";
      return fetchJson<CombatHelp>(
        `/bot/tactical/combat/${position}${q}`,
        "combat",
      );
    },
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
