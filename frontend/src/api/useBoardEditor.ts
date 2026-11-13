import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import type { MoveRouteData } from "@/domains/movement/routeTypes";
import { useCallback } from "react";
import { parseErrorDetail } from "@/api/apiError";
import { fetchJson } from "@/api/fetchJson";
import type { ObjectivePaymentBody } from "@/entities/data/types";
import { useAppStore } from "@/state/appStore";

/*
 * Akcje planszy. Część endpointów WALIDUJE reguły (ruch, produkcja, aktywacja,
 * flow, okna) i zwraca 422 z czytelnym powodem; część to God-Mode bez reguł
 * (edycja/przesuwanie jednostek). Odrzucenie walidacji pokazujemy graczowi jako
 * ``notice`` (baner w panelu), zamiast ciche połykać błąd.
 */
const BOT_ROOT = "/bot";

async function postRaw(path: string, body: unknown): Promise<Response> {
  const response = await fetch(`${BOT_ROOT}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const raw = await response.text().catch(() => "");
    const message = parseErrorDetail(raw, response.status);
    // Pokaż graczowi powód (np. „system już aktywowany", „za mało zasobów").
    useAppStore.getState().setNotice(message, "error");
    throw new Error(message);
  }
  return response;
}

async function post(path: string, body: unknown): Promise<void> {
  await postRaw(path, body);
}

/** Jedna strona transakcji: to, co dany gracz ODDAJE partnerowi (RULES.md 47). */
export type TransactionSide = {
  tradeGoods: number;
  commodities: number;
  promissoryNote: string | null;
  relicFragments: string[];
  /** Karty akcji (Arbiters / Black Market Dealings) — inaczej silnik odrzuci (422). */
  actionCards?: string[];
  /** Karty planet (Pride of Kenara): ``"<planeta>><planeta docelowa jednostek>"``. */
  planets?: string[];
};

/** Propozycja transakcji czekająca na zgodę partnera (RULES.md 47.1a). */
export type TransactionOfferView = {
  proposer: string;
  partner: string;
  proposerColor: string | null;
  partnerColor: string | null;
  /** null, gdy oglądający nie jest stroną transakcji (zawartość prywatna). */
  give: TransactionSide | null;
  receive: TransactionSide | null;
  /** Pride of Kenara: oddawane przez partnera planety -> jego możliwe cele jednostek. */
  unitDestinations?: Record<string, string[]>;
};

export type TransactionPartnerView = {
  playerId: string;
  color: string | null;
  /** Sąsiad czy efekt bez sąsiedztwa (Guild Ships / Trade Convoys). */
  neighbor: boolean;
  /** Czy w tej parze wolno wymieniać karty akcji (Arbiters / Black Market Dealings). */
  actionCards: boolean;
  done: boolean;
  /** Planety, których kartę ten partner może oddać (Pride of Kenara). */
  planets: string[];
};

export type TransactionStateView = {
  offer: TransactionOfferView | null;
  partners: TransactionPartnerView[];
  /** Planety, których kartę aktywny gracz może oddać (Pride of Kenara). */
  myPlanets: string[];
  /** Notki, o które mogę poprosić partnera (jego ręka ukryta, RULES.md 47.1a). */
  requestableNotes?: string[];
};

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
  /** Przełom frakcji (Thunder's Edge). */
  breakthrough_unlocked?: boolean;
  breakthrough_exhausted?: boolean;
  breakthrough_tg?: number;
  /** Promissory notes w strefie gracza (play area) — jawne, odrębne od ręki. */
  promissory_notes_in_play?: string[];
  /** Relikty przed graczem (God-Mode, nadpisuje listę). */
  relics?: string[];
  /** Fragmenty reliktów w strefie gracza - id kart eksploracji (God-Mode, nadpisuje listę). */
  relic_fragments?: string[];
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
      "moveRoute",
      "spaceCannon",
      "transactionState",
      "battle",
      "capacity",
      "fleetPool",
      "playerHand",
      "actionCardPlayable",
      "relicPlayable",
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

  // --- Faza statusu (RULES.md 41) ---

  // Krok 1: gracz, którego kolej, zdobywa cel publiczny albo tajny.
  const statusScore = useCallback(
    async (
      playerId: string,
      kind: "public" | "secret",
      objectiveId: string,
      payment?: ObjectivePaymentBody,
    ) => {
      await post("/status/score", {
        player_id: playerId,
        kind,
        objective_id: objectiveId,
        // Bez `payment` silnik dobiera płatność sam (cele bez kosztu go nie potrzebują).
        ...(payment ? { payment } : {}),
      });
      await refresh();
    },
    [refresh],
  );

  // Krok 1: gracz kończy punktowanie; ostatni uruchamia kroki 2–4.
  const statusFinishScoring = useCallback(
    async (playerId?: string) => {
      await post("/status/finish-scoring", { player_id: playerId ?? null });
      await refresh();
    },
    [refresh],
  );

  // --- Epilog: głosowanie nad zwycięstwem honorowym / niehonorowym ---

  // Otwiera głosowanie (idempotentnie); boty głosują same.
  const epilogueOpen = useCallback(async () => {
    await post("/epilogue/open", {});
    await refresh();
  }, [refresh]);

  // Gracz (nie zwycięzca) oddaje głos.
  const epilogueVote = useCallback(
    async (playerId: string, choice: "honorable" | "dishonorable") => {
      await post("/epilogue/vote", { player_id: playerId, choice });
      await refresh();
    },
    [refresh],
  );

  // Krok 5: gracz zatwierdza rozdział WSZYSTKICH żetonów w pulach.
  const statusRedistribute = useCallback(
    async (
      playerId: string,
      pools: { tactical: number; fleet: number; strategic: number },
    ) => {
      await post("/status/redistribute", { player_id: playerId, ...pools });
      await refresh();
    },
    [refresh],
  );

  // --- Faza agendy (RULES.md 51) ---

  // Mówca ujawnia wierzchnią agendę i otwiera głosowanie.
  const agendaReveal = useCallback(
    async (playerId: string) => {
      await post("/agenda/reveal", { player_id: playerId });
      await refresh();
    },
    [refresh],
  );

  // Gracz, którego kolej, wyczerpuje planety i oddaje głosy na jeden wynik.
  const agendaVote = useCallback(
    async (playerId: string, outcome: string, planets: string[], usePredictive = false) => {
      await post("/agenda/vote", {
        player_id: playerId,
        outcome,
        planets,
        use_predictive: usePredictive,
      });
      await refresh();
    },
    [refresh],
  );

  // Gracz, którego kolej, wstrzymuje się od głosu.
  const agendaAbstain = useCallback(
    async (playerId: string) => {
      await post("/agenda/abstain", { player_id: playerId });
      await refresh();
    },
    [refresh],
  );

  // Mówca rozstrzyga remis / brak głosów (to nie jest głos).
  const agendaDecide = useCallback(
    async (playerId: string, outcome: string) => {
      await post("/agenda/decide", { player_id: playerId, outcome });
      await refresh();
    },
    [refresh],
  );

  // Mówca odrzuca agendę bez możliwych wyników i ujawnia następną.
  const agendaDiscard = useCallback(
    async (playerId: string) => {
      await post("/agenda/discard", { player_id: playerId });
      await refresh();
    },
    [refresh],
  );

  // Mówca: po wyniku - druga agenda albo (po drugiej) odświeżenie planet.
  const agendaContinue = useCallback(
    async (playerId: string) => {
      await post("/agenda/continue", { player_id: playerId });
      await refresh();
    },
    [refresh],
  );

  // Mówca potwierdza wynik czekający w kroku COUNTED (po oknie na karty reakcji).
  const agendaConfirm = useCallback(
    async (playerId: string) => {
      await post("/agenda/confirm", { player_id: playerId });
      await refresh();
    },
    [refresh],
  );

  const skipPhase = useCallback(async () => {
    await post("/phase/skip", {});
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

  const setSpeaker = useCallback(
    async (playerId: string) => {
      await post("/speaker/set", { player_id: playerId });
      await refresh();
    },
    [refresh],
  );

  // God-Mode: wymusza, czyja jest teraz kolejka (omija reguły kolejności tur).
  const setActivePlayer = useCallback(
    async (playerId: string) => {
      await post("/god-mode/patch", { active_player_id: playerId });
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
    async (playerId?: string, componentId?: string, params?: Record<string, unknown>) => {
      await post("/tactical/component-action", {
        player_id: playerId ?? null,
        component_id: componentId ?? null,
        params: params ?? {},
      });
      await refresh();
    },
    [refresh],
  );

  // Zagranie karty akcji z oknem „Action" jako akcji komponentu (RULES.md 53). Silnik waliduje
  // i stosuje efekt; ``implemented=false`` = karta bez automatyzacji (odrzucona, skutek ręcznie).
  const playActionCard = useCallback(
    async (
      playerId: string,
      cardId: string,
      params: Record<string, unknown>,
      /** Migawka historii: karta zagrana przez HOLD (cofnięcie do tego kroku). */
      seq?: number,
    ): Promise<{ implemented: boolean; held: boolean }> => {
      const response = await postRaw(seq === undefined ? "/action-card/play" : "/hold/play", {
        player_id: playerId,
        actor_id: playerId,
        card_id: cardId,
        params,
        ...(seq === undefined ? {} : { seq }),
      });
      const data = (await response.json()) as { implemented: boolean; held?: boolean };
      await refresh();
      return { implemented: data.implemented, held: data.held === true };
    },
    [refresh],
  );
  // Zagranie „ACTION:" reliktu jako akcji komponentu (RULES.md 59). Relikt zostaje przed graczem
  // (wyczerpany albo purge przez efekt); ``implemented=false`` = skutek rozstrzyga operator.
  const playRelic = useCallback(
    async (
      playerId: string,
      relicId: string,
      params: Record<string, unknown>,
      root: "/relic/play" | "/frontier-card/play" = "/relic/play",
    ): Promise<{ implemented: boolean }> => {
      const response = await postRaw(root, {
        player_id: playerId,
        actor_id: playerId,
        relic_id: relicId,
        params,
      });
      const data = (await response.json()) as { implemented: boolean };
      await refresh();
      return { implemented: data.implemented };
    },
    [refresh],
  );
  // Fragmenty -> relikt (RULES.md 59.7): purge zestawu fragmentów, akcja komponentu gracza.
  // Scenę odsłonięcia gra ``RelicRevealWatcher`` u wszystkich (stan ``relicReveal``).
  const forgeRelic = useCallback(
    async (playerId: string, fragments: string[]): Promise<string | null> => {
      const response = await postRaw("/relic/forge", {
        player_id: playerId,
        actor_id: playerId,
        fragments,
      });
      const data = (await response.json()) as { relic_id: string | null };
      await refresh();
      return data.relic_id;
    },
    [refresh],
  );
  // Transakcja z sąsiadem (RULES.md 47). ``give`` = co oddaje aktywny gracz, ``receive`` =
  // co dostaje od partnera. Backend egzekwuje reguły (sąsiad, 1/turę, stan posiadania) i
  // przy błędzie zwraca 422 → ``post`` pokazuje powód w komunikacie.
  // Transakcja ze zgodą partnera (RULES.md 47.1a): propozycja → przyjęcie/odrzucenie/wycofanie.
  const proposeTransaction = useCallback(
    async (args: {
      partnerId: string;
      give: TransactionSide;
      receive: TransactionSide;
    }) => {
      const side = (s: TransactionSide) => ({
        trade_goods: s.tradeGoods,
        commodities: s.commodities,
        promissory_note: s.promissoryNote,
        relic_fragments: s.relicFragments,
        action_cards: s.actionCards ?? [],
        planets: s.planets ?? [],
      });
      await post("/transactions/propose", {
        partner_id: args.partnerId,
        give: side(args.give),
        receive: side(args.receive),
      });
      await refresh();
    },
    [refresh],
  );

  const respondTransaction = useCallback(
    async (playerId: string, accept: boolean, planetDestinations: Record<string, string> = {}) => {
      await post("/transactions/respond", {
        player_id: playerId,
        accept,
        planet_destinations: planetDestinations,
      });
      await refresh();
    },
    [refresh],
  );

  const cancelTransaction = useCallback(
    async (playerId: string) => {
      await post("/transactions/cancel", { player_id: playerId });
      await refresh();
    },
    [refresh],
  );

  // Żetony długu (debt) (nieformalna zasada stołu, RULES.md 47.3): wystawca → posiadacz.
  const giveDebtTokens = useCallback(
    async (issuerId: string, holderId: string, count: number) => {
      await post("/debt/give", {
        issuer_id: issuerId,
        holder_id: holderId,
        count,
      });
      await refresh();
    },
    [refresh],
  );

  // Posiadacz zwraca wystawcy jego żetony (dług spłacony/odpuszczony).
  const returnDebtTokens = useCallback(
    async (holderId: string, issuerId: string, count: number) => {
      await post("/debt/return", {
        issuer_id: issuerId,
        holder_id: holderId,
        count,
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
      // ``fromPosition`` = system na trasie, z którego zabieramy ładunek (domyślnie źródło).
      cargo?: { baseType: string; count: number; fromZone?: string; fromPosition?: string }[];
      // Trasa wybrana przez gracza (systemy od źródła do aktywnego); brak = najkrótsza legalna.
      route?: string[];
    }) => {
      await post("/tactical/move", {
        fromPosition: args.fromPosition,
        gravityDrive: useAppStore.getState().gravityDrive,
        tempesta: useAppStore.getState().tempesta,
        imperator: useAppStore.getState().imperator,
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
            fromPosition: c.fromPosition ?? null,
          })),
        route: args.route ?? null,
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
      exhaustAida = false,
    ) => {
      await post("/tactical/produce", {
        faction,
        orders,
        spend,
        exhaust_aida: exhaustAida,
      });
      await refresh();
    },
    [refresh],
  );

  // Space Cannon Offense (RULES.md 38) — strzał (rzut kośćmi po stronie silnika), pas
  // i przypisanie strat przez gracza-cel. 422 z powodem trafia do panelu komunikatów.
  const spaceCannonFire = useCallback(
    async (
      faction: string,
      target?: string,
      exhaustGls = false,
      plasmaUnit: string | null = null,
    ) => {
      await post("/tactical/space-cannon/fire", {
        faction,
        target: target ?? null,
        exhaust_gls: exhaustGls,
        plasma_unit: plasmaUnit,
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
    async (
      faction: string,
      plan: {
        sustain: { baseType: string; count: number }[];
        destroy: { baseType: string; count: number }[];
        destroyDamaged: { baseType: string; count: number }[];
      },
    ) => {
      const clean = (items: { baseType: string; count: number }[]) =>
        items.filter((l) => l.count > 0);
      await post("/tactical/space-cannon/assign", {
        faction,
        losses: clean(plan.destroy),
        sustain: clean(plan.sustain),
        destroyDamaged: clean(plan.destroyDamaged),
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

  // Relikty nad rzutami rundy (RULES.md 59): przerzut z +1 (Crown of Thalnos) i ±1 do kości
  // (Heart of Ixth). Po rzucie, przed przypisaniem strat; silnik przelicza trafienia.
  const battleRelicReroll = useCallback(
    async (faction: string, picks: { entry: number; dice: number[] }[]) => {
      await post("/tactical/battle/relic-reroll", { faction, picks });
      await refresh();
    },
    [refresh],
  );

  const battleRelicAdjust = useCallback(
    async (args: {
      faction: string;
      target: string;
      entry: number;
      die: number;
      delta: 1 | -1;
    }) => {
      await post("/tactical/battle/relic-adjust", args);
      await refresh();
    },
    [refresh],
  );

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
  // Fleet pool (RULES.md 42): gracz zwraca nadwyżkę statków ponad pulę floty do rezerwy.
  const fleetPoolResolve = useCallback(
    async (faction: string, remove: Record<string, number>) => {
      await post("/tactical/fleet-pool/resolve", {
        faction,
        remove: Object.entries(remove)
          .filter(([, count]) => count > 0)
          .map(([baseType, count]) => ({ baseType, count })),
      });
      await refresh();
    },
    [refresh],
  );
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

  // Komponenty frakcji (RULES.md 61.3): ACTION lidera / zdolności / przełomu jako akcja tury.
  const playFactionComponent = useCallback(
    async (
      playerId: string,
      kind: string,
      componentId: string,
      params: Record<string, unknown>,
    ): Promise<{ implemented: boolean }> => {
      const response = await postRaw("/faction-component/play", {
        player_id: playerId,
        actor_id: playerId,
        kind,
        component_id: componentId,
        params,
      });
      const data = (await response.json()) as { implemented: boolean };
      await refresh();
      return { implemented: data.implemented };
    },
    [refresh],
  );
  // Lider, którego warunku silnik jeszcze nie sprawdza — gracz odblokowuje sam (RULES.md 61.1).
  const claimLeaderUnlock = useCallback(
    async (playerId: string, leaderId: string) => {
      await post("/leader/claim-unlock", {
        player_id: playerId,
        actor_id: playerId,
        leader_id: leaderId,
      });
      await refresh();
    },
    [refresh],
  );
  // Promissory note z ręki (RULES.md 61.2): reakcja w otwartym oknie albo ACTION.
  const playPromissory = useCallback(
    async (
      playerId: string,
      noteId: string,
      params: Record<string, unknown>,
    ): Promise<{ implemented: boolean }> => {
      const response = await postRaw("/promissory/play", {
        player_id: playerId,
        actor_id: playerId,
        note_id: noteId,
        params,
      });
      const data = (await response.json()) as { implemented: boolean };
      await refresh();
      return { implemented: data.implemented };
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

  // Wybór aktywnego gracza dla bieżącego kroku wieloetapowego primary (RULES.md 30.5).
  const strategyPrimaryStep = useCallback(
    async (playerId: string, payload: Record<string, unknown>) => {
      await post("/strategy/primary-step", {
        player_id: playerId,
        payload,
      });
      await refresh();
    },
    [refresh],
  );

  const strategySecondary = useCallback(
    async (playerId: string, execute: boolean, payload: Record<string, unknown> = {}) => {
      await post("/strategy/secondary", {
        player_id: playerId,
        execute,
        payload,
      });
      await refresh();
    },
    [refresh],
  );

  // --- Setup startowy (tajne cele, żeton Custodians, odkrycie celów; RULES.md 45) ---

  const setupSecret = useCallback(
    async (playerId: string, objectiveId: string) => {
      await post("/setup/secret", {
        player_id: playerId,
        objective_id: objectiveId,
      });
      await refresh();
    },
    [refresh],
  );

  const setupCustodians = useCallback(
    async (playerId: string) => {
      await post("/setup/custodians", { player_id: playerId });
      await refresh();
    },
    [refresh],
  );

  const setupRevealObjectives = useCallback(
    async (playerId: string) => {
      await post("/setup/reveal-objectives", { player_id: playerId });
      await refresh();
    },
    [refresh],
  );

  const setupSkip = useCallback(async () => {
    await post("/setup/skip", {});
    await refresh();
  }, [refresh]);

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
    statusScore,
    statusFinishScoring,
    agendaReveal,
    agendaVote,
    agendaAbstain,
    agendaDecide,
    agendaDiscard,
    agendaContinue,
    agendaConfirm,
    epilogueOpen,
    epilogueVote,
    statusRedistribute,
    nextPhase,
    skipPhase,
    nextRound,
    pickStrategyCard,
    playStrategyCard,
    setSpeaker,
    setActivePlayer,
    playComponentAction,
    playActionCard,
    playRelic,
    playFactionComponent,
    claimLeaderUnlock,
    playPromissory,
    forgeRelic,
    proposeTransaction,
    respondTransaction,
    cancelTransaction,
    giveDebtTokens,
    returnDebtTokens,
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
    battleRelicReroll,
    battleRelicAdjust,
    battleClose,
    battleAnnounceRetreat,
    battleRetreat,
    capacityResolve,
    fleetPoolResolve,
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
    strategyPrimaryStep,
    setupSecret,
    setupCustodians,
    setupRevealObjectives,
    setupSkip,
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
  /** Trafienia, które strona może jeszcze przyjąć (jednostki + Sustain Damage × anulowane). */
  hp: number;
  /** Ile trafień anuluje jedno użycie Sustain Damage (1; Non-Euclidean Shielding: 2). */
  sustainCancels?: number;
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
  phase: "AFB" | "AMBUSH" | "COMBAT" | "RETREAT";
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
  /** Jednorazowe efekty poza rundami (Assault Cannon) — do animacji. */
  effects?: BattleEffect[];
  /**
   * TYLKO klient: kości/strzały ostatniej salwy jeszcze lecą — wynik (kto trafił, ile trafień
   * pokryć) czeka na koniec animacji (``useDiceHold`` w ``BattleOverlay``).
   */
  resolving?: boolean;
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
  /** Relikty zmieniające kości po rzucie, przed przypisaniem strat (RULES.md 59). */
  relicTools?: { faction: string; tool: "reroll" | "adjust" }[];
  /**
   * Zdolności frakcji zmieniające kości rundy, dostępne TERAZ (np. Munitions Reserves po
   * opłaceniu 2 TG): wybór kości ``min..max`` i użycie przez ``/faction-component/play``.
   */
  abilityTools?: BattleAbilityTool[];
};

/** Efekt komponentu w walce (np. Assault Cannon: kto strzela, czyj statek, jaki typ). */
export type BattleEffect = {
  kind: string;
  player: string;
  victim: string;
  unit: string;
};

export type BattleAbilityTool = {
  faction: string;
  /** Silnikowe id gracza (``player_id`` dla ``/faction-component/play``). */
  playerId: string;
  kind: "leader" | "ability" | "breakthrough";
  componentId: string;
  name: string;
  text: string;
  min: number;
  max: number;
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
  /** Fighter II: myśliwce ponad capacity liczą się do fleet pool, nie są nadwyżką capacity. */
  fightersToFleet?: boolean;
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

// --- Fleet pool (RULES.md 42) ---

export type FleetShip = {
  baseType: string;
  asyncId: string;
  name: string;
  count: number;
};

export type FleetPoolView = {
  /** true = trwa okno FLEET_POOL (usunięcie wymuszone); false = tylko ostrzeżenie. */
  active: boolean;
  known: boolean;
  position: string | null;
  player: string | null;
  playerId: string | null;
  /** Żetony w puli floty = maks. liczba statków nie-myśliwskich w systemie. */
  pool: number;
  /** Limit puli nie obowiązuje (np. Darktalon Treilla do końca rundy). */
  unlimited?: boolean;
  total: number;
  excess: number;
  ships: FleetShip[];
  /** Podpowiedź „Auto" (najtańsze statki najpierw). */
  suggestion: Record<string, number>;
  remaining: number;
  /** Pojemność w przestrzeni systemu (RULES.md 39.6) - prognoza dla produkcji. */
  capacity: {
    /** Pojemność statków. */
    general: number;
    /** Miejsca doków TYLKO dla myśliwców (np. „do 3 myśliwców nie liczy się"). */
    fighterOnly: number;
    fighters: number;
    fighterCost: number;
    /** Zajęta pojemność przez resztę ładunku (piechota, mechy w przestrzeni). */
    otherLoad: number;
    /** Fighter II: myśliwce ponad capacity liczą się do fleet pool. */
    fightersToFleet?: boolean;
    /** Myśliwce ponad capacity już teraz liczone do fleet pool (Fighter II). */
    fleetFighters?: number;
    excess: number;
  };
};

/**
 * Stan fleet pool: respondent okna FLEET_POOL albo aktywny gracz w aktywnym systemie
 * (ostrzeżenie w produkcji / ruchu, zanim nadwyżka zostanie wymuszona).
 */
export function useFleetPool(enabled: boolean) {
  return useQuery<FleetPoolView>({
    queryKey: ["fleetPool"],
    enabled,
    queryFn: async () =>
      fetchJson<FleetPoolView>("/bot/tactical/fleet-pool", "fleetPool"),
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
  /** Klucz grupy - wybór jednostki z dodatkową kością (Plasma Scoring). */
  key: string;
  /** Ile kości dodałby Plasma Scoring jednej jednostce tej grupy (0 = brak technologii). */
  plasmaDice: number;
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
  /** Modyfikator wyniku każdej kości (Antimass Deflectors celu: -1). */
  modifier: number;
  /** Kości dodane przez Plasma Scoring. */
  extraDice: number;
};

export type SpaceCannonPending = {
  roller: string;
  target: string;
  hits: number;
  /** Ile trafień pokryć: min(trafienia, statki celu + Sustain Damage). */
  required: number;
  rolls: SpaceCannonRoll[];
  /** Ile trafień anuluje jedno użycie Sustain Damage celu (Non-Euclidean Shielding: 2). */
  cancels?: number;
};

export type SpaceCannonShip = {
  baseType: string;
  asyncId: string;
  name: string;
  count: number;
  /** Ile już uszkodzonych. */
  damaged?: number;
  /** Czy typ może jeszcze użyć Sustain Damage. */
  sustain?: boolean;
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

/**
 * Stan transakcji (RULES.md 47.1a): propozycja w toku i partnerzy aktywnego gracza. ``stamp``
 * (np. publiczny skrót propozycji z web-data) wymusza odświeżenie, gdy ktoś inny coś zmieni.
 */
export function useTransactionState(stamp: string, player: string | null = null) {
  return useQuery<TransactionStateView>({
    queryKey: ["transactionState", stamp, player],
    staleTime: 0,
    queryFn: () =>
      fetchJson<TransactionStateView>(
        `/bot/transactions/state${player ? `?player=${encodeURIComponent(player)}` : ""}`,
        "transactionState",
      ),
  });
}

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
export function useMoveRange(
  faction: string | null,
  enabled: boolean,
  gravityDrive = false,
  tempesta = false,
  imperator = false,
) {
  return useQuery<MoveRange>({
    queryKey: ["moveRange", faction, gravityDrive, tempesta, imperator],
    enabled: enabled && faction !== null,
    queryFn: async () =>
      fetchJson<MoveRange>(
        `/bot/tactical/move-range?faction=${encodeURIComponent(faction ?? "")}&gravity_drive=${gravityDrive}&tempesta=${tempesta}&imperator=${imperator}`,
        "moveRange",
      ),
    staleTime: 0,
  });
}

/**
 * Podgląd trasy ruchu (RULES.md 32.1, 32.3): trasa przez waypointy ``via``, alternatywy,
 * statki ze źródła (czy dolecą) i ładunek leżący po drodze. Zero mutacji stanu gry.
 */
export function useMoveRoute(
  faction: string | null,
  from: string | null,
  via: string[],
  gravityDrive: boolean,
  tempesta: boolean,
  imperator = false,
) {
  return useQuery<MoveRouteData>({
    queryKey: ["moveRoute", faction, from, via, gravityDrive, tempesta, imperator],
    enabled: faction !== null && from !== null,
    queryFn: async () =>
      fetchJson<MoveRouteData>(
        `/bot/tactical/move-route?faction=${encodeURIComponent(faction ?? "")}&from_position=${encodeURIComponent(from ?? "")}&via=${encodeURIComponent(via.join(","))}`,
        "moveRoute",
      ),
    placeholderData: keepPreviousData,
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

export type ActivityFact = {
  /** vp, tech, planet_gained/lost, tg + jawne karty: action_card, agenda,
   *  explore_card, relic_fragment, promissory_in_play, objective_revealed,
   *  secret_scored + zasoby/plansza: commodities, cc, hand, units, system_token,
   *  relic, frontier_card, leader, breakthrough_unlocked, strategy_card_gained,
   *  law_enacted, law_repealed, attached, objective_scored, effect, speaker,
   *  custodians_removed, winner. Pełna lista: `core/activity.py`. */
  type: string;
  /** Null dla zdarzeń talii/stołu bez jednego właściciela. */
  player_id: string | null;
  value: string | null;
  delta: number | null;
  /** Kontekst, np. talia eksploracji. */
  detail: string | null;
};

export type ActivityKind =
  | "turn"
  | "strategy"
  | "tactical"
  | "combat"
  | "economy"
  | "scoring"
  | "exploration"
  | "misc"
  | "godmode";

export type Activity = {
  kind: ActivityKind;
  action: string;
  actor_id: string | null;
  target_id: string | null;
  subject: string | null;
  detail: string | null;
  round: number;
  phase: string;
  facts: ActivityFact[];
};

export type ActivityEntry = {
  seq: number;
  is_current: boolean;
  /** Sekundy epoki; null dla migawek sprzed wprowadzenia feedu. */
  created_at: number | null;
  activity: Activity;
};

export type ActivityPlayer = {
  faction: string | null;
  color: string | null;
  display_name: string;
  is_bot: boolean;
};

export type ActivityFeed = {
  entries: ActivityEntry[];
  players: Record<string, ActivityPlayer>;
  /** Bieżąca migawka; wpisy o większym `seq` są cofnięte (gałąź redo). */
  current_seq: number | null;
};

/**
 * Feed „kto co zrobił" (powiadomienia o akcjach graczy). Klucz zaczyna się od
 * ``history``, więc każda mutacja, która unieważnia historię, odświeża też feed.
 */
export function useActivityFeed() {
  return useQuery<ActivityFeed>({
    queryKey: ["history", "activity"],
    queryFn: () =>
      fetchJson<ActivityFeed>("/bot/history/activity", "activity feed"),
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
