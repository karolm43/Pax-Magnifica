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
  return raw || `Error ${status}`;
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
  /** Promissory notes w strefie gracza (play area) — jawne, odrębne od ręki. */
  promissory_notes_in_play?: string[];
};

/**
 * Hook z akcjami edycji planszy (God-Mode). Każda akcja po sukcesie inwaliduje
 * dokument web-data, więc plansza i panele odświeżają się natychmiast.
 */
export function useBoardEditor() {
  const queryClient = useQueryClient();

  const refresh = useCallback((): Promise<void> => {
    // WAŻNE (UX): NIE czekamy na zakończenie refetchy. `invalidateQueries`
    // zwraca Promise rozwiązywany dopiero, gdy wszystkie zapytania się
    // przeładują — wcześniej `await refresh()` trzymał przycisk w stanie
    // `disabled` na czas pełnego round-tripu („cooldown" po kliknięciu). Teraz
    // tylko OZNACZAMY zapytania jako nieświeże (react-query przeładuje je w tle)
    // i od razu zwracamy rozwiązany Promise, więc akcja kończy się tuż po
    // sukcesie POST. Klucze: stan gracza, historia, karty strategii, walka,
    // produkcja i ręka gracza (pasek ręki = ręka AKTYWNEGO gracza, po zmianie tury).
    for (const key of [
      "playerData",
      "history",
      "strategyCards",
      "combat",
      "production",
      "moveRange",
      "spaceCannon",
      "battle",
      "capacity",
      "playerHand",
    ]) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
    return Promise.resolve();
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

  // Przekazuje aktywność następnemu graczowi (initiative order) BEZ oznaczania
  // „skończył fazę" — tylko STATUS/AGENDA. Zasila „Next player" w AGENDZIE
  // (operator przewija graczy, nikogo nie kończąc).
  const nextPlayer = useCallback(
    async (playerId?: string) => {
      await post("/turn/next-player", { player_id: playerId ?? null });
      await refresh();
    },
    [refresh],
  );

  // Bieżący gracz KOŃCZY swoją część fazy STATUS/AGENDA (passed=True) i przekazuje
  // dalej. Zasila „Next player" (STATUS: gracz zrobił swój krok) oraz „Pass"
  // (AGENDA: gracz zrezygnował z reakcji/głosu). Dzięki temu all_passed wykrywa
  // komplet i mówca dostaje „Next phase" (DECYZJA PROJEKTOWA 2026-11).
  const phaseStep = useCallback(
    async (playerId?: string) => {
      await post("/turn/phase-step", { player_id: playerId ?? null });
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

  // Akcja komponentu (RULES.md 31.8) — trzeci typ akcji fazy akcji. NA RAZIE szkielet:
  // tylko rejestruje „gracz wykonał akcję komponentu w tej turze" (odblokowuje End turn),
  // bez mechaniki konkretnego komponentu. ``componentId`` to adnotacja „co zagrano"
  // (karta akcji / relikt / tech / zdolność), opcjonalna.
  const playComponentAction = useCallback(
    async (playerId?: string, componentId?: string) => {
      await post("/tactical/component-action", {
        player_id: playerId ?? null,
        component_id: componentId ?? null,
      });
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
      faction: string;
      // Pojedynczy stos (zgodność wsteczna) — opcjonalny, gdy używamy ``ships``.
      baseType?: string;
      count?: number;
      // Pełna flota ruszająca naraz (typy statków) — dla dedykowanego okna ruchu.
      ships?: { baseType: string; count: number }[];
      // Ładunek: myśliwce / siły naziemne przewożone razem (RULES.md 32.3).
      // ``fromZone`` = "space" albo id planety (pickup z planety systemu źródłowego).
      // Limit capacity egzekwuje backend (422 z powodem, gdy przekroczony).
      cargo?: { baseType: string; count: number; fromZone?: string }[];
    }) => {
      await post("/tactical/move", {
        fromPosition: args.fromPosition,
        baseType: args.baseType ?? null,
        count: args.baseType ? (args.count ?? 1) : 0,
        faction: args.faction,
        ships: (args.ships ?? [])
          .filter((s) => s.count > 0)
          .map((s) => ({ baseType: s.baseType, count: s.count })),
        cargo: (args.cargo ?? [])
          .filter((c) => c.count > 0)
          .map((c) => ({
            baseType: c.baseType,
            count: c.count,
            fromZone: c.fromZone ?? "space",
          })),
      });
      await refresh();
    },
    [refresh],
  );

  // Produkcja WALIDOWANA (RULES.md 33.2-33.3) — limit/blokada/strefy/rezerwa/koszt; 422 gdy
  // nielegalna. `spend` = planety do wyczerpania + TG (bez niego silnik płaci sam).
  const produce = useCallback(
    async (
      faction: string,
      orders: { baseType: string; count: number; zone?: string }[],
      spend?: { planets: string[]; tradeGoods: number },
    ) => {
      await post("/tactical/produce", { faction, orders, spend });
      await refresh();
    },
    [refresh],
  );

  // Space Cannon Offense (RULES.md 38) — strzał (rzut kośćmi po stronie silnika), pas
  // i przypisanie strat przez gracza-cel. 422 z powodem trafia do panelu komunikatów.
  const spaceCannonFire = useCallback(
    async (faction: string, target?: string) => {
      await post("/tactical/space-cannon/fire", {
        faction,
        target: target ?? null,
      });
      await refresh();
    },
    [refresh],
  );

  const spaceCannonPass = useCallback(
    async (faction: string) => {
      await post("/tactical/space-cannon/pass", { faction });
      await refresh();
    },
    [refresh],
  );

  const spaceCannonAssign = useCallback(
    async (faction: string, losses: { baseType: string; count: number }[]) => {
      await post("/tactical/space-cannon/assign", {
        faction,
        losses: losses
          .filter((l) => l.count > 0)
          .map((l) => ({ baseType: l.baseType, count: l.count })),
      });
      await refresh();
    },
    [refresh],
  );

  // Walka (RULES.md 39) — start, AFB, rzuty, pokrycie trafień, zamknięcie. Rzuty po
  // stronie silnika; 422 z powodem trafia do panelu komunikatów.
  const battleStart = useCallback(
    async (planet?: string | null) => {
      await post("/tactical/battle/start", { planet: planet ?? null });
      await refresh();
    },
    [refresh],
  );

  const battleAfb = useCallback(async () => {
    await post("/tactical/battle/afb", {});
    await refresh();
  }, [refresh]);

  const battleRoll = useCallback(async () => {
    await post("/tactical/battle/roll", {});
    await refresh();
  }, [refresh]);

  const battleAssign = useCallback(
    async (faction: string, plan: BattleAssignPlan) => {
      const items = (m: Record<string, number>) =>
        Object.entries(m)
          .filter(([, count]) => count > 0)
          .map(([baseType, count]) => ({ baseType, count }));
      await post("/tactical/battle/assign", {
        faction,
        sustain: items(plan.sustain),
        destroy: items(plan.destroy),
        destroyDamaged: items(plan.destroyDamaged),
      });
      await refresh();
    },
    [refresh],
  );

  const battleClose = useCallback(async () => {
    await post("/tactical/battle/close", {});
    await refresh();
  }, [refresh]);

  // Limit pojemności (RULES.md 39.6): gracz usuwa nadwyżkę ładunku z przestrzeni systemu.
  const capacityResolve = useCallback(
    async (faction: string, remove: Record<string, number>) => {
      await post("/tactical/capacity/resolve", {
        faction,
        remove: Object.entries(remove)
          .filter(([, count]) => count > 0)
          .map(([baseType, count]) => ({ baseType, count })),
      });
      await refresh();
    },
    [refresh],
  );

  // Odwroty (RULES.md 39.5): ogłoszenie / walka dalej, potem wykonanie do sąsiedniego systemu.
  const battleAnnounceRetreat = useCallback(
    async (faction: string, announce: boolean) => {
      await post("/tactical/battle/announce-retreat", { faction, announce });
      await refresh();
    },
    [refresh],
  );

  const battleRetreat = useCallback(
    async (faction: string, destination: string) => {
      await post("/tactical/battle/retreat", { faction, destination });
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

  // God-Mode: ustawia prywatną rękę gracza (karty akcji / sekrety / weksle).
  // Głównie do testów „paska ręki" na mapie. Pominięte listy zostają bez zmian.
  const setPlayerHand = useCallback(
    async (
      playerId: string,
      hand: {
        actionCards?: string[];
        secretObjectives?: string[];
        promissoryNotes?: string[];
      },
    ) => {
      await post("/player/hand/set", {
        player_id: playerId,
        action_cards: hand.actionCards ?? null,
        secret_objectives: hand.secretObjectives ?? null,
        promissory_notes: hand.promissoryNotes ?? null,
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
    nextPlayer,
    phaseStep,
    nextPhase,
    nextRound,
    pickStrategyCard,
    playStrategyCard,
    setSpeaker,
    playComponentAction,
    activateSystem,
    moveShips,
    produce,
    spaceCannonFire,
    spaceCannonPass,
    spaceCannonAssign,
    battleStart,
    battleAfb,
    battleRoll,
    battleAssign,
    battleClose,
    battleAnnounceRetreat,
    battleRetreat,
    capacityResolve,
    tacticalNextStep,
    tacticalSetStep,
    endTactical,
    placeCommandToken,
    capturePlanet,
    togglePlanetExhaust,
    toggleTechExhaust,
    setLeaderState,
    setPlayerHand,
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
  /** Łączna wartość PRODUCTION jednostek gracza w aktywnym systemie (limit sztuk). */
  productionLimit: number;
  units: ProducibleUnitHelp[];
};

// --- Walka: okno pola bitwy (RULES.md 39) ---

export type BattleUnit = {
  baseType: string;
  asyncId: string;
  name: string;
  count: number;
  damaged: number;
  /** Próg trafienia PO modyfikatorze (np. mgławica obrońcy). */
  hitsOn: number;
  baseHitsOn: number;
  modifier: number;
  dicePerUnit: number;
  totalDice: number;
  expectedHits: number;
  sustain: boolean;
  sustainable: number;
  afbHitsOn: number | null;
  afbDice: number;
};

export type BattleSide = {
  faction: string;
  playerId: string;
  role: "attacker" | "defender";
  units: BattleUnit[];
  unitCount: number;
  totalDice: number;
  expectedHits: number;
  /** Trafienia, które strona może jeszcze przyjąć (jednostki + Sustain Damage). */
  hp: number;
};

export type BattleRoll = {
  baseType: string;
  asyncId: string;
  name: string;
  hitsOn: number;
  modifier: number;
  dice: number[];
  hits: number;
};

export type BattleLogEntry = {
  round: number;
  phase: "AFB" | "COMBAT" | "RETREAT";
  rolls: Record<string, BattleRoll[]>;
  hits: Record<string, number>;
  losses: Record<string, Record<string, number>>;
  sustained: Record<string, Record<string, number>>;
  /** Wykonany odwrót (tylko wpis RETREAT): strona, system, przeniesione jednostki. */
  retreat: {
    player: string;
    destination: string;
    units: Record<string, number>;
    tokenPlaced: boolean;
  } | null;
};

/** Dozwolony system odwrotu (RULES.md 39.5 O4). */
export type RetreatOption = { position: string; systemId: string };

export type BattleView = {
  active: boolean;
  kind: "space" | "ground" | null;
  position: string | null;
  planet: string | null;
  round: number;
  step: "AFB" | "ANNOUNCE" | "ROLL" | "ASSIGN" | "RETREAT" | "DONE" | null;
  nebula: boolean;
  attacker: BattleSide | null;
  defender: BattleSide | null;
  pendingHits: Record<string, number>;
  /** Ile trafień gracz musi pokryć (min(trafienia, jednostki + Sustain)). */
  required: Record<string, number>;
  /** Gracz, który teraz pokrywa trafienia (okno COMBAT_ASSIGN_HITS). */
  assigning: string | null;
  rolls: Record<string, BattleRoll[]>;
  afb: Record<string, BattleRoll[]>;
  log: BattleLogEntry[];
  winner: string | null;
  outcome: "winner" | "draw" | null;
  /** Kto teraz ogłasza odwrót (okno COMBAT_RETREAT; obrońca, potem atakujący). */
  announcing: string | null;
  /** Strony, które ogłosiły odwrót w tej rundzie (wykonanie w kroku RETREAT). */
  retreating: string[];
  /** Wykonane odwroty: strona → system docelowy. */
  retreated: Record<string, string>;
  /** Dozwolone cele odwrotu per strona (pusta lista = nie może się wycofać). */
  retreatOptions: Record<string, RetreatOption[]>;
};

/** Plan pokrycia trafień: Sustain Damage + niszczone nieuszkodzone/uszkodzone (baseType → liczba). */
export type BattleAssignPlan = {
  sustain: Record<string, number>;
  destroy: Record<string, number>;
  destroyDamaged: Record<string, number>;
};

/** Stan okna pola bitwy (strony, jednostki, rzuty, straty, historia). */
export function useBattle(enabled: boolean) {
  return useQuery<BattleView>({
    queryKey: ["battle"],
    enabled,
    queryFn: async () =>
      fetchJson<BattleView>("/bot/tactical/battle", "battle"),
    staleTime: 0,
  });
}

// --- Limit pojemności (RULES.md 39.6) ---

export type CapacityCargo = {
  baseType: string;
  asyncId: string;
  name: string;
  count: number;
  /** Ile pojemności zajmuje jedna sztuka (capacityUsed). */
  cost: number;
};

export type CapacityView = {
  active: boolean;
  position: string | null;
  /** Klucz encji (kolor) bieżącego respondenta okna CAPACITY. */
  player: string | null;
  playerId: string | null;
  /** Pojemność statków (ogólna). */
  general: number;
  /** Przydział doków na planetach — tylko dla myśliwców. */
  fighterOnly: number;
  used: number;
  excess: number;
  cargo: CapacityCargo[];
  /** Podpowiedź „Auto" (najtańsze jednostki najpierw). */
  suggestion: Record<string, number>;
  remaining: number;
};

/** Stan okna limitu pojemności (kto usuwa nadwyżkę i z czego wybiera). */
export function useCapacity(enabled: boolean) {
  return useQuery<CapacityView>({
    queryKey: ["capacity"],
    enabled,
    queryFn: async () =>
      fetchJson<CapacityView>("/bot/tactical/capacity", "capacity"),
    staleTime: 0,
  });
}

// --- Space Cannon Offense (RULES.md 38) ---

export type SpaceCannonShooter = {
  baseType: string;
  asyncId: string;
  name: string;
  count: number;
  hitsOn: number;
  dicePerUnit: number;
  totalDice: number;
  expectedHits: number;
  position: string;
  zone: string;
  /** Wariant ma Deep Space Cannon (może strzelać z systemu sąsiedniego). */
  deep: boolean;
  /** Strzela z systemu SĄSIEDNIEGO do aktywnego. */
  remote: boolean;
};

export type SpaceCannonSide = {
  faction: string;
  playerId: string;
  shooters: SpaceCannonShooter[];
  totalDice: number;
  expectedHits: number;
  /** Legalne cele (klucze graczy). */
  targets: string[];
};

export type SpaceCannonRoll = {
  baseType: string;
  asyncId: string;
  name: string;
  hitsOn: number;
  position: string;
  zone: string;
  dice: number[];
  hits: number;
};

export type SpaceCannonPending = {
  roller: string;
  target: string;
  hits: number;
  /** Ile statków trzeba zniszczyć: min(trafienia, statki celu). */
  required: number;
  rolls: SpaceCannonRoll[];
};

export type SpaceCannonShip = {
  baseType: string;
  asyncId: string;
  name: string;
  count: number;
};

export type SpaceCannonLogEntry = {
  roller: string;
  target: string;
  hits: number;
  passed: boolean;
  rolls: SpaceCannonRoll[];
  destroyed: Record<string, number>;
};

export type SpaceCannonPanel = {
  position: string | null;
  isOpen: boolean;
  /** Okno zamknięte, ale było rozstrzygnięcie (dziennik niepusty). */
  resolved: boolean;
  queue: string[];
  responded: string[];
  current: string | null;
  sides: SpaceCannonSide[];
  pending: SpaceCannonPending | null;
  targetShips: SpaceCannonShip[];
  log: SpaceCannonLogEntry[];
};

/** Stan panelu Space Cannon Offense (kolejka, strzelcy, straty do przypisania, dziennik). */
export function useSpaceCannon(enabled: boolean) {
  return useQuery<SpaceCannonPanel>({
    queryKey: ["spaceCannon"],
    enabled,
    queryFn: async () =>
      fetchJson<SpaceCannonPanel>("/bot/tactical/space-cannon", "spaceCannon"),
    staleTime: 0,
  });
}

export type MoveRange = {
  active: string | null;
  /** {pozycja źródłowa -> lista base_type statków, które mogą stamtąd ruszyć}. */
  sources: Record<string, string[]>;
};

/**
 * Podgląd zasięgu ruchu (RULES.md 32): które systemy mają statki gracza mogące
 * legalnie ruszyć do aktywnego systemu. Do podświetlenia zasięgu/ścieżki na mapie.
 * Pusta mapa ``sources`` = brak legalnego ruchu (albo brak aktywnego systemu).
 */
export function useMoveRange(faction: string | null, enabled: boolean) {
  return useQuery<MoveRange>({
    queryKey: ["moveRange", faction],
    enabled: enabled && faction !== null,
    queryFn: async () =>
      fetchJson<MoveRange>(
        `/bot/tactical/move-range?faction=${encodeURIComponent(faction ?? "")}`,
        "moveRange",
      ),
    staleTime: 0,
  });
}

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
