import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchJson } from "@/api/fetchJson";
import type { ExtraDie } from "@/shared/ui/ExtraDicePicker";
import type { MoveRouteData } from "@/domains/movement/routeTypes";
import type { TransactionStateView } from "@/api/useBoardEditor";

/*
 * Zapytania planszy TYLKO do odczytu (react-query): walka, capacity, pula floty, transakcje,
 * Space Cannon, zasięg i trasa ruchu, produkcja, karty strategii, feed Activity, czat, historia.
 * Wydzielone z ``useBoardEditor.ts`` (który eksportuje je dalej); akcje zmieniające stan są tam.
 */

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
  phase: "AFB" | "AMBUSH" | "BOMBARDMENT" | "COMBAT" | "RETREAT";
  /** Zdolność wpisu spoza rund (np. „Harrow” przy BOMBARDMENT w walce naziemnej). */
  label?: string;
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

/** Wymuszony cel trafień (``BattleView.hitTargets``) — logika w ``battleAssign``. */
export type HitTarget = {
  types: string[];
  count: number;
  label: string;
  damaged: boolean | null;
  chooser: string;
};

/** Dozwolony system odwrotu (RULES.md 39.5 O4). */
export type RetreatOption = {
  position: string;
  systemId: string;
  /** Odwrót przez Ion Storm w systemie z własnym wormholem tego typu: gracz wybiera wormhole. */
  ionStormChoice?: boolean;
};

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
  /** Walka czeka na reakcje po Sustain Damage ostatniej strony (Direct Hit, Reflective). */
  sustainHold?: boolean;
  /**
   * Wymuszony cel trafień strony (Devotion: statek wskazany przez Yin; Impulse Core:
   * nie-myśliwce). Brak wpisu = strona przypisuje dowolnie.
   */
  hitTargets?: Record<string, HitTarget>;
  rolls: Record<string, BattleRoll[]>;
  afb: Record<string, BattleRoll[]>;
  /** Dodatkowe kości AFB do przypisania przed rzutem (klucz = strona walki, RULES.md 62.11). */
  afbExtra?: Record<string, (ExtraDie & { pick: string })[]>;
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
  kind: "leader" | "ability" | "breakthrough" | "technology";
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
  /** Źródła dodatkowych kości (Plasma Scoring, commander Argent, Ambuscade) - każde osobno. */
  extraDice?: ExtraDie[];
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
 * Stoły transakcji gracza ``player`` (RULES.md 47.1b) i gracze, z którymi może usiąść. ``stamp``
 * (publiczny skrót stołów z web-data) wymusza odświeżenie, gdy ktoś inny coś położy.
 */
export function useTransactionState(stamp: string, player: string | null = null) {
  return useQuery<TransactionStateView>({
    queryKey: ["transactionState", stamp, player],
    staleTime: 0,
    // Klucz zmienia się po każdym ruchu przy stole - bez tego dane na chwilę znikały i cały
    // stół odmontowywał się i wracał (skakanie i miganie przy dokładaniu weksli).
    placeholderData: keepPreviousData,
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
   *  custodians_removed, fracture_entered, winner. Pełna lista: `core/activity.py`. */
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
  /** Pełna nazwa frakcji (uzupełniana na froncie z web-data; pierwszeństwo przed `display_name`). */
  faction_name?: string;
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

/** Wiadomość czatu z perspektywy oglądającego (RULES.md 47.6): cudzy szept ma ``text = null``. */
export type ChatMessage = {
  seq: number;
  sender: string;
  /** Adresat szeptu; ``null`` = do wszystkich. */
  to: string | null;
  whisper: boolean;
  text: string | null;
  /** Czas wysłania (s UNIX, zegar serwera). */
  at: number;
  /** Komunikat frakcji: gotowa kwestia z pola gracza (publiczna, z dymkiem). */
  voice?: boolean;
};

/** Dziennik czatu oglądającego ``player`` (w sieci serwer i tak bierze gracza z tokenu). */
export function useChat(player: string | null) {
  return useQuery<ChatMessage[]>({
    queryKey: ["chat", player],
    queryFn: async () => {
      const data = await fetchJson<{ messages: ChatMessage[] }>(
        `/bot/chat${player ? `?player=${encodeURIComponent(player)}` : ""}`,
        "chat",
      );
      return data.messages;
    },
    staleTime: 0,
    placeholderData: keepPreviousData,
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
