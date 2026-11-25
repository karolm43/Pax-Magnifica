import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { parseErrorDetail } from "@/api/apiError";
import type { ObjectivePaymentBody } from "@/entities/data/types";
import { useAppStore } from "@/state/appStore";
import type { BattleAssignPlan } from "@/api/boardQueries";
import type { MoveLegRequest } from "@/domains/movement/flightPlan";

export * from "@/api/boardQueries";

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

/** Strona stołu transakcji: to, co dany gracz POŁOŻYŁ (oddaje partnerowi) — RULES.md 47.1b. */
export type TransactionSide = {
  tradeGoods: number;
  commodities: number;
  promissoryNote: string | null;
  relicFragments: string[];
  /** Karty akcji (Arbiters / Black Market Dealings) — inaczej silnik odrzuci (422). */
  actionCards?: string[];
  /** Relikty i niezdobyte tajne cele (Black Market Dealings). */
  relics?: string[];
  secretObjectives?: string[];
  /** Karty planet (Pride of Kenara): ``"<planeta>><planeta docelowa jednostek>"``. */
  planets?: string[];
  /** Przechwycone statki/mechy PARTNERA zwracane mu (typy bazowe, RULES.md 61.5). */
  capturedUnits?: string[];
  /** Ile SWOICH żetonów długu kładę (RULES.md 47.3 — pamięć stołu). */
  debtTokens?: number;
  /** Krok 3 Trade: posiadacz karty daje darmowe secondary (RULES.md 47.4). */
  tradeSecondary?: boolean;
  /** Krok 3 Trade: obietnica „wash −N” (null = bez wash). */
  wash?: number | null;
};

/** Stół, przy którym siedzę: obie strony, Ready i co wolno położyć (RULES.md 47.1b). */
export type TransactionTableView = {
  partner: string;
  partnerColor: string | null;
  mine: TransactionSide;
  theirs: TransactionSide;
  myReady: boolean;
  theirReady: boolean;
  /** Wolno kłaść komponenty (inaczej tylko żetony długu). */
  components: boolean;
  actionCards: boolean;
  extras: boolean;
  /** Krok 3 Trade: ja jestem posiadaczem karty / partner jest. */
  tradeHolder: boolean;
  tradePartner: boolean;
  /** Umowa Trade może obejmować komponenty i wash (sąsiad / Guild Ships). */
  dealComponents: boolean;
  /** Stół otwarty sam po uzupełnieniu commodities (umowa Trade). */
  prefilled: boolean;
  /** Moje relikty, które wolno położyć (Black Market Dealings / The Silver Flame). */
  tradableRelics?: string[];
};

export type TransactionPartnerView = {
  playerId: string;
  color: string | null;
  /** Sąsiad (albo Guild Ships / Trade Convoys) — inaczej stół tylko na dług. */
  neighbor: boolean;
  /** Wolno teraz wymieniać komponenty. */
  components: boolean;
  done: boolean;
};

export type TransactionStateView = {
  tables: TransactionTableView[];
  partners: TransactionPartnerView[];
  /** Planety, których kartę mogę oddać (Pride of Kenara). */
  myPlanets: string[];
  /** Gracze wskazani umową w kroku 3 Trade. */
  dealPlayers: string[];
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

  /** „Undo last move" w kroku ruchu — aktywny gracz cofa własny ostatni ruch (nie tylko host). */
  const undoMove = useCallback(async () => {
    await post("/tactical/undo-move", {});
    await refresh();
  }, [refresh]);

  /** God-Mode: włącza/wyłącza limit ręki kart akcji (RULES.md 53.8). */
  const setActionCardLimitDisabled = useCallback(
    async (disabled: boolean) => {
      await post("/god-mode/patch", { action_card_limit_disabled: disabled });
      await refresh();
    },
    [refresh],
  );

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

  // God-Mode (testy): tura przechodzi do następnego gracza bez akcji i pasa.
  const skipPlayer = useCallback(async () => {
    await post("/turn/skip-player", {});
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
    async (playerId: string, initiative: number, recipient?: string) => {
      await post("/strategy/pick", {
        player_id: playerId,
        initiative,
        // Checks and Balances: kto dostaje wybraną kartę (RULES.md 51.6).
        ...(recipient ? { recipient } : {}),
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
  // Stół transakcji (RULES.md 47.1b): każda strona kładzie własne rzeczy, dwa Ready = wymiana.
  // Backend egzekwuje reguły i przy błędzie zwraca 422 → ``post`` pokazuje powód.
  const openTable = useCallback(
    async (playerId: string, partnerId: string) => {
      await post("/transactions/table/open", { player_id: playerId, partner_id: partnerId });
      await refresh();
    },
    [refresh],
  );

  const setTableSide = useCallback(
    async (playerId: string, partnerId: string, s: TransactionSide) => {
      await post("/transactions/table/side", {
        player_id: playerId,
        partner_id: partnerId,
        side: {
          trade_goods: s.tradeGoods,
          commodities: s.commodities,
          promissory_note: s.promissoryNote,
          relic_fragments: s.relicFragments,
          action_cards: s.actionCards ?? [],
          planets: s.planets ?? [],
          captured_units: s.capturedUnits ?? [],
          debt_tokens: s.debtTokens ?? 0,
          trade_secondary: s.tradeSecondary ?? false,
          wash: s.wash ?? null,
        },
      });
      await refresh();
    },
    [refresh],
  );

  const setTableReady = useCallback(
    async (playerId: string, partnerId: string, ready: boolean) => {
      await post("/transactions/table/ready", {
        player_id: playerId,
        partner_id: partnerId,
        ready,
      });
      await refresh();
    },
    [refresh],
  );

  const closeTable = useCallback(
    async (playerId: string, partnerId: string) => {
      await post("/transactions/table/close", { player_id: playerId, partner_id: partnerId });
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

  // Czat i szepty (RULES.md 47.6): to nie stan gry - odświeżamy tylko dziennik czatu.
  const sendChat = useCallback(
    async (playerId: string, text: string, to: string | null, voice = false) => {
      await post("/chat/send", { player_id: playerId, text, to, voice });
      await queryClient.invalidateQueries({ queryKey: ["chat"] });
    },
    [queryClient],
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
      // Ion Storm z własnym wormholem systemu: true = przez żeton, false = własny wormhole.
      ionStormToken?: boolean;
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
        ionStormToken: args.ionStormToken ?? null,
      });
      await refresh();
    },
    [refresh],
  );

  /** Whole flight plan of the Move Ships step at once (RULES.md 32.4): all legs or nothing. */
  const moveBatch = useCallback(
    async (faction: string, legs: MoveLegRequest[]) => {
      await post("/tactical/move-batch", { faction, legs });
      await refresh();
    },
    [refresh],
  );

  // Produkcja WALIDOWANA (RULES.md 33.2-33.3) — limit/blokada/strefy/rezerwa/koszt; 422 gdy
  // nielegalna. `spend` = planety do wyczerpania + TG (bez niego silnik płaci sam).
  const produce = useCallback(
    async (
      faction: string,
      orders: { baseType: string; count: number; zone?: string; sources?: string[] }[],
      spend?: { planets: string[]; tradeGoods: number },
      exhaustAida = false,
      // Amalgamation (RULES.md 62.17): {typ: {właściciel | "token": sztuki}} zamiast zasobów.
      captured: Record<string, Record<string, number>> = {},
      // Tungstantus (RULES.md 62.18): 1 TG przed zapłatą.
      commanderTradeGood = false,
    ) => {
      await post("/tactical/produce", {
        faction,
        orders,
        spend,
        exhaust_aida: exhaustAida,
        captured,
        commander_trade_good: commanderTradeGood,
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
      extraDice: Record<string, string> | null = null,
    ) => {
      await post("/tactical/space-cannon/fire", {
        faction,
        target: target ?? null,
        exhaust_gls: exhaustGls,
        extraDice,
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

  // Dodatkowe kości AFB (commander Argent, Strike Wing Ambuscade): wybór per źródło przed rzutem.
  const battleAfbExtraDice = useCallback(
    async (playerId: string, picks: Record<string, string>) => {
      await post("/tactical/battle/afb/extra-dice", { playerId, picks });
      await refresh();
    },
    [refresh],
  );

  // ``faction`` = rzuca tylko ta strona (drugą kliknie jej gracz); brak = obie naraz.
  const battleRoll = useCallback(
    async (faction?: string) => {
      await post("/tactical/battle/roll", faction ? { faction } : {});
      await refresh();
    },
    [refresh],
  );

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
  // R_capture notes/5 (RULES.md 61.5): own captured units back to reinforcements at any time.
  const captureReturnOwn = useCallback(
    async (faction: string, baseType: string, count = 1) => {
      await post("/capture/return-own", { faction, baseType, count });
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
    async (faction: string, destination: string, ionStormToken?: boolean) => {
      await post("/tactical/battle/retreat", {
        faction,
        destination,
        ionStormToken: ionStormToken ?? null,
      });
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
    undoMove,
    setActionCardLimitDisabled,
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
    skipPlayer,
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
    openTable,
    setTableSide,
    setTableReady,
    closeTable,
    returnDebtTokens,
    sendChat,
    activateSystem,
    moveShips,
    moveBatch,
    produce,
    spaceCannonFire,
    spaceCannonPass,
    spaceCannonAssign,
    battleStart,
    battleAfb,
    battleAfbExtraDice,
    battleRoll,
    battleAssign,
    battleRelicReroll,
    battleRelicAdjust,
    battleClose,
    battleAnnounceRetreat,
    battleRetreat,
    capacityResolve,
    fleetPoolResolve,
    captureReturnOwn,
    tacticalNextStep,
    tacticalSetStep,
    endTactical,
    placeCommandToken,
    capturePlanet,
    togglePlanetExhaust,
    toggleTechExhaust,
    setLeaderState,
    setPlayerHand,
    strategySecondary,
    strategyPrimaryStep,
    setupSecret,
    setupCustodians,
    setupRevealObjectives,
    setupSkip,
    closeWindow,
  };
}
