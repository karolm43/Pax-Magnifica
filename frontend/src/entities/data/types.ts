export type Point = { x: number; y: number };

export type RGBColor = { red: number; green: number; blue: number };

/** Unit counts by state: [healthy, damaged, galvanized, galvanized + damaged]. */
export type StateCounts = [number, number, number, number];

export type Breakthrough = {
  alias: string;
  name: string;
  displayName?: string;
  faction: string;
  synergy: string[];
  text: string;
  source: string;
};
type PlanetType =
  | "FACTION"
  | "CULTURAL"
  | "INDUSTRIAL"
  | "HAZARDOUS"
  | "NONE"
  | "MR"
  | "SPACESTATION"
  | "FAKE";

export type TileData = {
  id: string;
  name?: string | null;
  aliases?: string[] | null;
  imagePath: string;
  planets?: string[];
  shipPositionsType?: string | null;
  spaceTokenLocations?: Point[] | null;
  wormholes?: (string | null)[] | null;
  isHyperlane?: boolean;
  isAsteroidField?: boolean;
  isSupernova?: boolean;
  isNebula?: boolean;
  isGravityRift?: boolean;
  isScar?: boolean;
  hasEgress?: boolean;
  imageURL?: string;
  source: string;
  tileBack?: string;
  valid?: boolean;
};

export type EntityData = {
  entityId: string;
  entityType: "unit" | "token" | "attachment" | "actioncard";
  count: number;
  unitStates?: StateCounts;
  sustained?: number | null;
};

export type Unit = {
  id: string;
  baseType: string;
  asyncId: string;
  name: string;
  source: string;
  upgradesToUnitId?: string;
  upgradesFromUnitId?: string;
  requiredTechId?: string;
  faction?: string;
  subtitle?: string;
  moveValue?: number;
  capacityValue?: number;
  capacityUsed?: number;
  cost?: number;
  combatHitsOn?: number;
  combatDieCount?: number;
  afbHitsOn?: number;
  afbDieCount?: number;
  bombardHitsOn?: number;
  bombardDieCount?: number;
  spaceCannonHitsOn?: number;
  spaceCannonDieCount?: number;
  sustainDamage?: boolean;
  canBeDirectHit?: boolean;
  planetaryShield?: boolean;
  deepSpaceCannon?: boolean;
  disablesPlanetaryShield?: boolean;
  isShip?: boolean;
  isGroundForce?: boolean;
  isStructure?: boolean;
  isMonument?: boolean;
  isPlanetOnly?: boolean;
  isSpaceOnly?: boolean;
  productionValue?: string | number;
  basicProduction?: string;
  ability?: string;
  imageURL?: string;
  bgDecalPath?: string;
  homebrewReplacesID?: string;
  fleetSupplyBonus?: number;
  eligiblePlanetTypes?: string[];
  unlock?: string;
};

export type Token = {
  id: string;
  imagePath: string;
  spaceOrPlanet?: string;
  aliasList?: string[];
  source: string;
  attachmentID?: string;
  wormholes?: string[];
  isAnomaly?: boolean;
  isRift?: boolean;
  isNebula?: boolean;
  isScar?: boolean;
  isNova?: boolean;
  isAsteroids?: boolean;
  tokenPlanetName?: string;
  isPlanet?: boolean;
  scale?: number;
  placement?: "rim" | "center";
};

export type Tech = {
  alias: string;
  name: string;
  types: string[];
  source: string;
  text: string;
  imageURL?: string;
  requirements?: string;
  faction?: string;
  baseUpgrade?: string;
  initials?: string;
  shortName?: string;
  shrinkName?: boolean;
  homebrewReplacesID?: string;
};

export type Relic = {
  alias: string;
  name: string;
  text: string;
  imageURL?: string;
  source: string;
  flavourText?: string;
  shrinkName?: boolean;
  shortName?: string;
  homebrewReplacesID?: string;
  isFakeRelic?: boolean;
  actualSource?: string;
};

export type FactionUnits = {
  [factionName: string]: EntityData[];
};

export type PlanetEntityData = {
  controlledBy: string | null;
  entities: FactionUnits;
  commodities: number | null;
  planetaryShield: boolean;
  exhausted?: boolean;
  resources: number | null;
  influence: number | null;
};

type PlanetData = {
  [planetName: string]: PlanetEntityData;
};

export type Leader = {
  id: string;
  type: string;
  tgCount: number;
  exhausted: boolean;
  locked: boolean;
  /** Bohater zużyty (RULES.md 61.1) — usunięty z gry. */
  purged?: boolean;
  active: boolean;
};

export type LeaderData = {
  id: string;
  faction: string;
  type: string;
  name: string;
  title: string;
  abilityWindow: string;
  abilityText: string;
  unlockCondition: string;
  source: string;
  shortName?: string;
  abilityName?: string;
  shrinkName?: boolean;
  searchTags?: string[];
  homebrewReplacesID?: string;
  tfName?: string;
  tfTitle?: string;
  tfAbilityWindow?: string;
  tfAbilityText?: string;
};

export type CapturedUnitsData = {
  [factionColor: string]: string[];
};

export type CapacityUsage = {
  total: number;
  used: number;
  ignored: number;
};

export type TileUnitData = {
  space: FactionUnits;
  planets: PlanetData;
  ccs: string[];
  anomaly: boolean;
  production: { [factionColor: string]: number };
  capacity?: {
    [factionColor: string]: CapacityUsage;
  };
  pds: {
    [factionName: string]: { count: number; expected: number };
  } | null;
};

export type LawInPlay = {
  id: string;
  name: string;
  uniqueId: number;
  type: string;
  target: string;
  text1: string;
  text2: string;
  mapText: string;
  electedInfo: string | null;
  electedFaction: string | null;
  electedType: string | null;
  controlTokens: string[];
  displaysElectedFaction: boolean;
};

export type StrategyCard = {
  initiative: number;
  name: string;
  id: string;
  picked: boolean;
  played: boolean;
  exhausted: boolean;
  tradeGoods: number;
  pickedByFaction: string | null;
};

export type CardPoolData = {
  secretObjectiveDeckSize: number;
  secretObjectiveFullDeckSize: number;
  secretObjectiveDeck: string[];
  secretObjectiveDiscard: string[];
  actionCardDeckSize: number;
  actionCardFullDeckSize: number;
  actionCardDiscardSize: number;
  actionCardPurgedSize: number;
  /** Karty akcji w talii (posortowane - nie zdradzają kolejności) i na stosie odrzuconych. */
  actionCardDeck?: string[];
  actionCardDiscard?: string[];
  /** Wspólny stos kart PURGE'owanych (eksploracja, akcje...). */
  purgedCards?: string[];
  /** Wierzch każdej talii eksploracji (klucz = talia) - używa go tylko tryb debug. */
  exploreTop?: Record<string, string>;
  culturalExploreDeck: string[];
  culturalExploreDiscard: string[];
  industrialExploreDeck: string[];
  industrialExploreDiscard: string[];
  hazardousExploreDeck: string[];
  hazardousExploreDiscard: string[];
  frontierExploreDeck: string[];
  frontierExploreDiscard: string[];
  relicDeckSize: number;
  relicFullDeckSize: number;
  relicDeck: string[];
  relicDiscard: string[];
  agendaDeckSize: number;
  agendaFullDeckSize: number;
  agendaDiscardSize: number;
  /** Wariant talii agend gry: "standard" (PoK) albo "absol". */
  agendaVariant?: string;
  technologyDeck: string[];
};

export type EntryType =
  | "PO_1"
  | "PO_2"
  | "SECRET"
  | "CUSTODIAN"
  | "IMPERIAL"
  | "CROWN"
  | "LATVINIA"
  | "SFTT"
  | "SHARD"
  | "STYX"
  | "AGENDA";

export type EntryState = "SCORED" | "QUALIFIES" | "POTENTIAL" | "UNSCORED";

export type ScoreBreakdownEntry = {
  type: EntryType;
  objectiveKey?: string;
  agendaKey?: string;
  description: string;
  state: EntryState;
  losable: boolean;
  currentProgress?: number;
  totalProgress?: number;
  pointValue: number;
  tombInPlay?: boolean;
  canDrawSecret?: boolean;
};

export type WebScoreBreakdown = {
  entries: ScoreBreakdownEntry[];
};

type Expedition = {
  completedBy: string | null;
};

export type Expeditions = {
  techSkip: Expedition;
  tradeGoods: Expedition;
  fiveRes: Expedition;
  fiveInf: Expedition;
  secret: Expedition;
  actionCards: Expedition;
};

export type BorderAnomalyInfo = {
  tile: string;
  direction: number;
  type: string; // e.g., "void_tether", "spatial_tear", etc.
};

export type PlayerDataResponse = {
  expeditions: Expeditions;
  ringCount: number;
  playerData: PlayerData[];
  tileUnitData: Record<string, TileUnitData>;
  tilePositions: string[];
  statTilePositions: Record<string, string[]>;
  lawsInPlay: LawInPlay[];
  strategyCards: StrategyCard[];
  strategyCardIdMap?: Record<number, string>; // Map of initiative -> strategy card ID
  vpsToWin: number;
  objectives: Objectives;
  cardPool: CardPoolData;
  versionSchema?: number;
  gameRound: number;
  gameName: string;
  gameCustomName?: string;
  tableTalkJumpLink?: string;
  actionsJumpLink?: string;
  scoreBreakdowns?: Record<string, WebScoreBreakdown>;
  borderAnomalies?: BorderAnomalyInfo[];
  isTwilightsFallMode?: boolean;
  gameState?: GameState;
  /** Increments whenever new game events are available; used to invalidate the events query without polling. */
  eventSequence?: number;
  /** Zegar szachowy graczy (RULES.md 58); null, gdy gra jest bez zegara. */
  chessClock?: ChessClockView | null;
};

/** Zegar jednego gracza — wartości aktualne na chwilę zbudowania dokumentu. */
export type ChessClockPlayer = {
  playerId: string;
  /** Klucz tożsamości (jak `playerData[].faction`). */
  faction: string;
  color: string | null;
  name: string;
  /** Pozostały czas; może być ujemny (przekroczenie nie jest karane). */
  remainingMs: number;
  /** Czas bieżącej tury (tylko holder, inaczej 0). */
  turnMs: number;
  /** Czy zegar tego gracza teraz tyka (UI dolicza upływ od odbioru dokumentu). */
  running: boolean;
};

export type ChessClockView = {
  paused: boolean;
  holderId: string | null;
  initialMs: number;
  incrementMs: number;
  players: ChessClockPlayer[];
};

type GameEventArchetype =
  | "TACTICAL_ACTION"
  | "TURN"
  | "CARD_PLAY_ACTION_CARD"
  | "CARD_PLAY_PROMISSORY_NOTE"
  | "CARD_PLAY_AGENT"
  | "CARD_PLAY_HERO"
  | "CARD_PLAY_RELIC"
  | "CARD_PLAY_TECH_EXHAUST"
  | "CARD_PLAY_BREAKTHROUGH"
  | "CARD_PLAY_ABILITY"
  | "TECH_RESEARCHED"
  | "SC_PLAYED"
  | "SC_PICKED"
  | "OBJECTIVE_SCORED"
  | "STATUS_SCORING"
  | "AGENDA_RESOLVED"
  | "TRANSACTION"
  | "PRODUCTION"
  | "MANUAL_COMMAND"
  | "PHASE_STARTED"
  | "ROUND_STARTED"
  | "GAME_ENDED";

/** Structured sub-events embedded in TACTICAL_ACTION payloads (payload.subEvents). */
export type GameSubEvent =
  | {
      type: "COMBAT";
      kind: "space" | "ground";
      tile: string | null;
      planet: string | null;
      vsFaction: string;
    }
  | { type: "CONTROL_ESTABLISHED"; planet: string; faction?: string }
  | {
      type: "ACTION_CARD_PLAYED";
      faction: string;
      cardId: string;
      cardName: string;
    }
  | {
      type: "LEADER_PLAYED";
      faction: string;
      leaderType: "AGENT" | "HERO";
      leaderId: string;
    }
  | { type: "TECH_EXHAUSTED"; faction: string; techId: string }
  | {
      type: "OBJECTIVE_SCORED";
      faction: string;
      objectiveId: string;
      category: "PUBLIC" | "SECRET" | "CUSTODIAN" | (string & {});
    }
  | {
      type: "PRODUCTION";
      tile: string | null;
      units: Record<string, number> | null;
      cost: number | null;
    }
  | {
      type: "RETREAT";
      faction: string;
      fromTile: string;
      fromHolder: string;
      toTile: string;
      toHolder: string;
      units: Record<string, StateCounts>;
    }
  | { type: "MANUAL_COMMAND"; user: string | null; command: string };

export type GameEvent = {
  seq: number;
  archetype: GameEventArchetype | (string & {});
  round: number;
  phase: string;
  faction: string | null;
  timestamp: number;
  payload: Record<string, unknown>;
  mapState?: string | null;
  movementState?: string | null;
};

export type GamePhase =
  | "unknown"
  | "setup.draft"
  | "setup.players"
  | "strategy"
  | "action"
  | "status.scoring"
  | "status.homework"
  | "agenda.readyToFlip"
  | "agenda.whens"
  | "agenda.afters"
  | "agenda.voting"
  | "agenda.resolving"
  | "finished";

export type GameStateAgenda = {
  id: string;
  startVoteCounts: Record<string, number>;
  castVoteCounts: Record<string, number>;
  outcomeVoteCounts: Record<string, number>;
  resolvedOutcome: string | null;
};

export type GameStateCombat = {
  system: string | null;
  unitHolder: string | null;
  round: number | null;
  participantColors: string[];
};

export type GameState = {
  phase: GamePhase;
  activePlayer: string | null;
  /**
   * Kolor gracza, którego jest TURA — w odróżnieniu od ``activePlayer`` NIE gaśnie,
   * gdy ten gracz już spasował w tej fazie. Panel sterowania turą (End turn/Pass)
   * używa tego pola, by wiedzieć „czyja tura", nawet gdy aktywny gracz zagrał kartę
   * i spasował, a okno secondary jeszcze trwa (RULES.md 31.4/31.6). ``activePlayer``
   * nadal służy do PODŚWIETLENIA (gaśnie dla spasowanego).
   */
  activeTurnPlayer?: string | null;
  /** Mówca (kolor) — otwiera wybór kart w fazie strategii (speaker order). */
  speaker?: string | null;
  /** Kolejność miejsc przy stole jako kolory (speaker order rotuje od mówcy). */
  seatingOrder?: string[];
  turnStartedAt: number | null;
  winner: string | null;
  agenda: GameStateAgenda | null;
  activeSystem: string | null;
  /** Bieżący krok akcji taktycznej (rozszerzenie Custodian Engine, E3). */
  tacticalStep?: string | null;
  activeCombat: GameStateCombat | null;
  /** Trwająca inwazja (Custodian Engine, RULES.md 40) — null, gdy brak. */
  activeInvasion?: { system: string; phase: string } | null;
  /** Trwająca eksploracja planet po Establish Control (Custodian Engine, RULES.md 46). */
  activeExploration?: { system: string } | null;
  /** Thunder's Edge (Custodian Engine, RULES.md 50): sygnał dla okien Fracture / Thunder's Edge. */
  thundersEdge?: {
    fractureInPlay: boolean;
    pendingIngress: boolean;
    pendingPlacement: boolean;
    lastRoll: { playerId: string; result: number; success: boolean; seq: number } | null;
    thundersEdgePosition: string | null;
  };
  /** Ostatni rzut kośćmi poza walką (Fracture, karty akcji) - animowany sceną kości. */
  tableRoll?: {
    seq: number;
    kind: string;
    /** `player_id` (`discordId`) rzucającego. */
    playerId: string;
    label: string;
    dice: number[];
    hitsOn: number | null;
    hitValues: number[] | null;
    summary: string;
  } | null;
  /**
   * Ostatnie odsłonięcie reliktu z talii (fragmenty, The Fracture, eksploracja) - scena
   * odsłonięcia u WSZYSTKICH graczy (`core.relics.record_reveal`, RULES.md 59.8).
   */
  relicReveal?: RelicReveal | null;
  /** Jednorazowa produkcja z karty (Freelancers) - okno produkcji poza krokiem PRODUCTION. */
  productionGrant?: { system: string; source: string } | null;
  /** Otwarte okno czasowe (timing window, Custodian Engine E8) — null, gdy brak. */
  pendingWindow?: PendingWindow | null;
  /**
   * Decyzje graczy (oferty technologii i zdolności, RULES.md 56) - null/puste, gdy brak.
   * Opcje wyborów pobiera okno decyzji z `GET /offers`; gracz zawsze decyduje sam.
   */
  /** Zużyto już premię Gravity Drive w tej akcji taktycznej (RULES.md 55.6). */
  gravityDriveUsed?: boolean;
  /** Aktywny gracz ma w tej akcji premię „+1 do ruchu jednego statku" z karty (Ionian Fuel Refinery). */
  extraMoveBoostActive?: boolean;
  /** Zużyto już premię Ionian Fuel Refinery w tej akcji taktycznej. */
  tempestaUsed?: boolean;
  /** Aktywny gracz ma premię ruchu przełomu Imperator (system z planetą legendarną). */
  imperatorBoostActive?: boolean;
  imperatorUsed?: boolean;
  pendingOffers?: { id: string; playerId: string; mandatory: boolean; label: string }[];
  /** Efekty trwałe w grze (bohater „near the game board”, kość agenta...) — panel przy planszy. */
  activeEffects?: ActiveEffectData[];
  /** Wieloetapowe primary karty strategii (wybory aktywnego gracza) — null, gdy brak. */
  pendingStrategy?: PendingStrategy | null;
  /** Zagrana karta akcji czekająca ~10 s na Sabotage (RULES.md 53.6) — null, gdy brak. */
  heldPlay?: HeldPlayData | null;
  /** Pauza ochronna w kluczowym oknie reakcji (RULES.md 54.10) — null, gdy brak. */
  reactionPause?: ReactionPauseData | null;
  /** Stoły transakcji (RULES.md 47.1b) — jawne pary, Ready i skrót zawartości (bez treści). */
  transactionTables?: {
    opener: string;
    partner: string;
    ready: string[];
    prefilled: boolean;
    stamp: number;
  }[];
  /** Setup startowy (tajne cele, żeton Custodians, odkrycie celów) — null po zakończeniu. */
  setup?: GameSetup | null;
  /**
   * Liczba kart strategii na gracza (``Pick_Count``) wyliczona z liczby graczy:
   * 2 przy 3–4 graczach, 1 przy 5–8. ``null``/brak, gdy liczba graczy jest spoza
   * 3..8 i wartość jest nieobsługiwana (web-data nie rzuca wtedy błędu). RULES.md 13.
   */
  strategyPickCount?: number | null;
  /**
   * Czy MÓWCA może już ogłosić przejście fazy — steruje widocznością „Next phase"
   * w panelu tury. Akcja/status: dopiero po komplecie pasów/kroków; strategia:
   * po pełnym wyborze kart; agenda: zawsze. (DECYZJA PROJEKTOWA 2026-11.)
   */
  canAdvancePhase?: boolean;
  /** Czy wszyscy gracze skończyli swoją część bieżącej fazy (pas/krok). */
  allPassed?: boolean;
  /** Stan kroków fazy statusu (RULES.md 41) — null poza zainicjowaną fazą statusu. */
  status?: StatusPhaseData | null;
  /** Faza agendy (RULES.md 51): ujawnienie, głosowanie, wynik — null poza nią. */
  agendaPhase?: AgendaPhaseData | null;
  /** Covert Legislation: ukryta agenda - tylko dla mówcy (null dla pozostałych). */
  agendaCovertCard?: AgendaPhaseData["card"];
  /** Search Warrant: jawne tajne cele właściciela ({player_id: [cele]}). */
  revealedSecrets?: Record<string, string[]>;
  /** Checks and Balances: wybraną kartę strategii dostaje inny gracz. */
  strategyGivesCards?: boolean;
  /** player_id zwycięzcy po zakończeniu gry (``winner`` to jego kolor). */
  winnerId?: string | null;
  /** God-Mode: limit ręki kart akcji wyłączony przez hosta (RULES.md 53.8). */
  actionCardLimitDisabled?: boolean;
  /** Dlaczego gra się skończyła (ekran zwycięstwa). */
  endReason?: "victory_points" | "round_limit" | "no_objectives" | null;
  /** Limit rund (0 = bez limitu). */
  maxRounds?: number;
  /** Głosowanie epilogu — null, dopóki gra trwa. */
  epilogue?: EpilogueData | null;
  /** Wnioski z przebiegu partii (największa bitwa, zdrady…) — puste, dopóki gra trwa. */
  highlights?: GameHighlight[];
};

export type GameHighlight = {
  key: string;
  title: string;
  detail: string;
  /** Krótka liczba/hasło do dużego napisu na karcie. */
  stat?: string;
  /** player_id uczestników (do ikon frakcji). */
  players: string[];
};

export type EpilogueChoice = "honorable" | "dishonorable";

export type EpilogueData = {
  /** player_id uprawnionych do głosu (wszyscy poza zwycięzcą), w kolejności przy stole. */
  voters: string[];
  /** player_id z drugiego miejsca — jego głos rozstrzyga remis. */
  runnerUp?: string | null;
  /** Oddane głosy: {player_id: wybór}. */
  votes: Record<string, EpilogueChoice>;
  /** Wynik, gdy zagłosowali wszyscy; null w trakcie. */
  result: EpilogueChoice | null;
};

/** Płatność za cel „Spend…" wysyłana do backendu (snake_case jak w API). */
export type ObjectivePaymentBody = {
  planets?: string[];
  trade_goods?: number;
  resource_planets?: string[];
  influence_planets?: string[];
  tokens?: Record<string, number>;
  cards?: string[];
  fragments?: string[];
};

/** Koszt celu „Spend…": co gracz może wydać + podpowiedź silnika (`suggested`). */
export type ObjectiveSpend = {
  kind: "trade_goods" | "tokens" | "resources" | "influence" | "mixed" | "cards" | "fragments";
  goal: number;
  tradeGoods: number;
  /** Wartość 1 TG w płatności wpływem/zasobami (Mirror Computing: 2). */
  tradeGoodValue?: number;
  planets?: Record<string, number>;
  resourcePlanets?: Record<string, number>;
  influencePlanets?: Record<string, number>;
  pools?: Record<string, number>;
  cards?: string[];
  fragments?: string[];
  suggested: ObjectivePaymentBody | null;
};

export type StatusObjectiveOption = {
  key: string;
  progress: number | null;
  threshold: number;
  ready: boolean;
  manual: boolean;
  /** Tylko cele z kosztem (Spend…): dane do okna wyboru płatności. */
  spend?: ObjectiveSpend | null;
};

export type StatusStepName = "SCORE_OBJECTIVES" | "REDISTRIBUTE" | "COMPLETE";

/**
 * Fazy statusu: kroki 1 (punktowanie) i 5 (żetony) są interaktywne, 2–4 i 6–7 wykonuje
 * silnik, krok 8 ogłasza mówca. Klucze map graczy to ``player_id`` (``discordId``).
 */
export type StatusPhaseData = {
  step: StatusStepName;
  scoredPublic: string[];
  scoredSecret: string[];
  done: string[];
  unassignedCc: Record<string, number>;
  fleetExcess: Record<string, Record<string, number>>;
  /** Statki liczone do fleet pool per gracz i system (podgląd zmiany puli, RULES.md 42). */
  fleetShips?: Record<string, Record<string, number>>;
  scoreablePublic: Record<string, string[]>;
  scoreableSecret: Record<string, string[]>;
  /** Cele do wyboru w kroku 1 per gracz: postęp względem karty (null = ręcznie). */
  publicOptions: Record<string, StatusObjectiveOption[]>;
  secretOptions: Record<string, StatusObjectiveOption[]>;
  /** Czy gracz kontroluje wszystkie planety domowe (warunek celów publicznych). */
  homeControlled: Record<string, boolean>;
  log: { step: number; label: string; [key: string]: unknown }[];
  isComplete: boolean;
  custodiansRemoved: boolean;
};

export type AgendaStepName =
  | "REVEAL"
  | "VOTE"
  | "TIEBREAK"
  | "COUNTED"
  | "RESOLVED"
  | "COMPLETE";

/** Rodzaj wyniku agendy wyliczony z pola `target` karty (core/agenda_phase.py). */
export type AgendaKind =
  | "for_against"
  | "player"
  | "player_or_against"
  | "player_techs"
  | "planet"
  | "planet_non_home"
  | "planet_non_home_not_mecatol"
  | "planet_trait"
  | "strategy_card"
  | "law"
  | "secret_objective"
  | "public_objective"
  | "tech_group"
  | "command_pool"
  | "manual";

export type AgendaVotePlanet = {
  planet: string;
  influence: number;
  exhausted: boolean;
};

/** Okno UI, w którym technologia jest istotna (zgodne z core/tech_effects.py). */
export type TechEffectContext =
  | "production"
  | "movement"
  | "combat"
  | "spaceCannon"
  | "invasion"
  | "agenda"
  | "fleet"
  | "status"
  | "turn"
  | "technology";

export type TechEffect = {
  alias: string;
  name: string;
  contexts: TechEffectContext[];
  /** active = działa stale, ready = gotowa do wyczerpania, exhausted = wyczerpana. */
  state: "active" | "ready" | "exhausted";
};

export type AgendaVoter = {
  planets: AgendaVotePlanet[];
  /** Wpływ gotowych planet (głosy do wydania). */
  available: number;
  total: number;
  /** Dodatkowe głosy z efektów gry (dziś 0). */
  extra: number;
  /** Predictive Intelligence: opcjonalne +3 głosy (decyzja gracza). */
  predictive: { owned: boolean; ready: boolean; votes: number };
  /** Representative Government: dokładnie 1 głos, bez planet i dodatkowych głosów. */
  singleVote?: boolean;
};

/** Rider zagrany na bieżącą agendę: kto, jaką kartą i NA JAKI wynik (jawne). */
export type AgendaPrediction = {
  playerId: string;
  card: string;
  cardName: string;
  outcome: string;
  outcomeLabel: string;
};

export type AgendaHistoryEntry = {
  number: number;
  agenda: string;
  kind?: AgendaKind;
  outcome?: string;
  bySpeaker?: boolean;
  stays?: boolean;
  discarded?: boolean;
  vetoed?: boolean;
  voided?: boolean;
  /** Covert Legislation: karta, pod którą głosowano nad ukrytą agendą. */
  covert?: string | null;
  /** Rozstrzygnięte riders tej agendy. */
  riders?: { player: string; card: string; predicted: string; correct: boolean; skipped?: string }[];
  totals?: Record<string, number>;
  votes?: Record<string, { outcome: string; votes: number }>;
};

/**
 * Faza agendy (RULES.md 51). Klucze graczy to `player_id` (`discordId`). Wszystko jest
 * jawne — głosy ogłasza się na głos (R_agenda_phase).
 */
export type AgendaPhaseData = {
  step: AgendaStepName;
  agendaNumber: number;
  totalAgendas: number;
  card: {
    id: string;
    name: string;
    type: string | null;
    target: string | null;
    text1: string | null;
    text2: string | null;
  } | null;
  kind: AgendaKind | "";
  outcomes: string[];
  unresolvable: boolean;
  /** Covert Legislation: głosuje się nad ukrytą agendą (treść widzi tylko mówca). */
  covert?: boolean;
  /** Riders zagrane na tę agendę (kto, czym, na jaki wynik). */
  predictions?: AgendaPrediction[];
  /** Miscount Disclosed: prawo, nad którym głosuje się ponownie po „dalej". */
  revoteLaw?: string | null;
  /** Gracze bez prawa głosu do końca fazy (Public Execution). */
  phaseBlocked?: string[];
  speakerId: string | null;
  voteOrder: string[];
  currentVoter: string | null;
  votes: Record<string, { outcome: string; votes: number; planets: string[] }>;
  abstained: string[];
  blocked: string[];
  tied: string[];
  totals: Record<string, number>;
  resolvedOutcome: string | null;
  /** Wynik policzony, czeka w kroku COUNTED na reakcje i potwierdzenie mówcy. */
  pendingOutcome?: string | null;
  /** Ostatni gracz, który oddał głosy (okno Distinguished Councilor). */
  lastVoteBy?: string | null;
  decidedBySpeaker: boolean;
  voters: Record<string, AgendaVoter>;
  history: AgendaHistoryEntry[];
  lawsInPlay: Record<string, string>;
  deckSize: number;
  deckSeeded: boolean;
  discardSize: number;
};

/**
 * Okno czasowe (timing window) — kolejka graczy reagujących po kolei (secondary
 * kart strategii, przypisanie strat w walce, space cannon, reakcje). Rozszerzenie
 * kontraktu Custodian Engine (RULES.md 29.2). ``currentResponder``/``queue`` to
 * KOLORY graczy (jak ``activePlayer``); ``currentResponderId`` to stabilny player_id
 * do adresowania odpowiedzi.
 */
export type PendingWindow = {
  windowType: string;
  currentResponder: string | null;
  currentResponderId: string | null;
  queue: string[];
  cursor: number;
  remaining: number;
  responded: string[];
  context: Record<string, string | number>;
  isComplete: boolean;
};

/**
 * Trwające WIELOETAPOWE primary karty strategii (RULES.md 30.5) — wybory aktywnego
 * gracza krok po kroku. ``ownerId`` (player_id) adresuje odpowiedź, ``ownerColor``
 * dopasowuje gracza w UI; ``step`` mówi, jaki wybór jest teraz wymagany.
 */
export type HeldPlayData = {
  /** Id graczy (jak ``actor_id``), nie kolory. */
  playerId: string;
  playerColor?: string;
  cardId: string;
  cardName: string;
  text: string;
  openedAt: number;
  holdSeconds: number;
  eligible: string[];
  passed: string[];
};

/** Pauza w kluczowym oknie (Coup, agenda, koniec bitwy, Sustain Damage) — gracze mogą reagować. */
export type ReactionPauseData = {
  key: string;
  /** Angielska etykieta okna, np. „After an agenda is revealed”. */
  label: string;
  event: string;
  subject: string | null;
  subjectColor: string | null;
  openedAt: number;
  pauseSeconds: number;
  /** Id graczy (jak ``actor_id``) pytanych o reakcję i tych, którzy spasowali. */
  eligible: string[];
  passed: string[];
};

export type PendingStrategy = {
  initiative: number;
  ownerId: string;
  ownerColor: string | null;
  step: string;
  draft: Record<string, unknown>;
};

export type GameStateMessage = {
  type: "gameState";
  seq: number;
  timestamp: number;
  full: boolean;
  /** Deep-partial merge patch of the full web-data document (PlayerDataResponse); the whole document when full=true. */
  patch: unknown;
};

export type BreakthroughData = {
  breakthroughId: string;
  unlocked: boolean;
  exhausted: boolean;
  tradeGoodsStored: number;
};

export type PlotCard = {
  plotAlias?: string;
  identifier: number;
  factions: string[];
};

/** Karta zdolności legendarnej planety w strefie gracza (RULES.md 60). */
export type LegendaryAbility = {
  planet: string;
  name: string;
  text: string;
  /** `action` = „ACTION:" (akcja komponentu); `passive` = oferty w oknie decyzji. */
  kind: "action" | "passive";
  exhausted: boolean;
};

export type PlayerData = {
  breakthrough?: BreakthroughData;
  plotCards?: PlotCard[];
  discordId: string;
  userName: string;
  faction: string;
  factionImage?: string;
  factionImageType?: string;

  color: string;
  displayName: string;
  isSpeaker: boolean;
  isTyrant: boolean;
  passed: boolean;
  /**
   * Czy gracz wykonał już akcję w BIEŻĄCEJ turze fazy akcji (RULES.md 31.7). UI
   * blokuje „End turn", dopóki to false i gracz nie spasował. Pole opcjonalne dla
   * zgodności ze starymi migawkami (brak = traktuj jak false).
   */
  tookActionThisTurn?: boolean;
  /**
   * Ile akcji zostało graczowi w bieżącej turze (bazowo 1; Fleet Logistics 2 — RULES.md 55.1).
   * Przyciski akcji są aktywne, dopóki > 0. Brak pola (stare migawki) = wg tookActionThisTurn.
   */
  actionsLeft?: number;
  eliminated: boolean;
  active: boolean;
  tacticalCC: number;
  fleetCC: number;
  strategicCC: number;
  ccReinf: number;
  tg: number;
  commodities: number;
  commoditiesTotal: number;
  crf: number;
  hrf: number;
  irf: number;
  urf: number;
  stasisInfantry: number;
  actualHits: number;
  expectedHitsTimes10: number;
  spaceArmyRes: number;
  groundArmyRes: number;
  spaceArmyHealth: number;
  groundArmyHealth: number;
  spaceArmyCombat: number;
  groundArmyCombat: number;

  // Pre-calculated planet economics
  resources: number;
  influence: number;
  totResources: number;
  totInfluence: number;
  optimalResources: number;
  optimalInfluence: number;
  flexValue: number;
  totOptimalResources: number;
  totOptimalInfluence: number;
  totFlexValue: number;

  unitsOwned: string[];
  /** Nazwa gracza (nie frakcji) i typ sterowania ("HUMAN" | "BOT") — Custodian Engine. */
  playerName?: string;
  controlType?: string;
  followedSCs: number[];
  unfollowedSCs: number[];
  promissoryNotesInPlayArea: string[];
  /** Prawa w strefie gracza (wygrane wybory „Elect Player", RULES.md 51) - id agend. */
  lawsOwned?: string[];
  customPromissoryNotes?: string[];
  techs: string[];
  exhaustedTechs: string[];
  /** Technologie istotne dla okien UI (silnik: core/tech_effects.py). */
  techEffects?: TechEffect[];
  factionTechs: string[];
  notResearchedFactionTechs: string[];
  planets: string[];
  exhaustedPlanets: string[];
  exhaustedPlanetAbilities: string[];
  fragments: string[];
  relics: string[];
  /** Karty frontier leżące u gracza (Enigmatic Device) - w ręce, zakładka Action cards. */
  frontierCards?: string[];
  exhaustedRelics: string[];
  /** Karty zdolności legendarnych planet gracza (RULES.md 60). */
  legendaryAbilities?: LegendaryAbility[];
  leaders: Leader[];
  leaderIDs: string[];
  secretsScored: Record<string, number>;
  knownUnscoredSecrets: Record<string, number>;
  numUnscoredSecrets: number;
  numScoreableSecrets: number;
  flexibleDisplayName: string;
  scs: number[];
  exhaustedSCs: number[];
  totalVps: number;
  neighbors: string[];
  /** Kolory graczy, z którymi gracz już transakcjonował w tej turze (RULES.md 47). */
  transactedWith?: string[];
  /** Fragmenty reliktów gracza (id + nazwa z katalogu) — wymiana w transakcjach. */
  relicFragmentCards?: { id: string; name: string }[];
  /** Żetony długu (debt), które gracz TRZYMA: {kolor wystawcy: liczba} (RULES.md 47.3). */
  debtTokens?: Record<string, number>;
  nombox?: CapturedUnitsData;
  abilities?: string[];
  decalId?: string;

  // card counts
  soCount: number;
  pnCount: number;
  acCount: number;
  /** Limit kart akcji w ręce (silnik: ``hand_limit.action_card_limit``); null = bez limitu. */
  actionCardLimit?: number | null;

  // unit counts (to get reinforcements total)
  unitCounts: Record<
    string,
    {
      unitCap: number;
      deployedCount: number;
    }
  >;

  // ghost-specific properties
  sleeperTokensReinf?: number;
  ghostWormholesReinf?: string[];
  breachTokensReinf?: number;
  galvanizeTokensReinf?: number;

  // mahact-specific properties
  mahactEdict?: string[];

  // nekro-specific properties (Thunder's Edge)
  valefarZTargets?: string[];

  // myko-mentori-specific properties (Divination omen dice results)
  omenDice?: number[];

  hasZeroToken?: boolean;
};

export type Planet = {
  id: string;
  tileId?: string | null;
  name: string;
  shortName?: string;
  shrinkName?: boolean;
  shortNamePNAttach?: string | null;
  shrinkNamePNAttach?: boolean | null;
  aliases: string[];
  positionInTile?: Point | null;
  resources: number;
  influence: number;
  factionHomeworld?: string | null;
  planetType?: PlanetType;
  planetTypes?: PlanetType[];
  cardImagePath?: string | null;
  techSpecialties?: string[] | null;
  legendaryAbilityName?: string | null;
  legendaryAbilityText?: string | null;
  legendaryAbilityFlavourText?: string | null;
  planetLayout?: {
    unitHolderName: string;
    resourcesLocation: "TopRight" | "BottomLeft" | "TopLeft" | "BottomRight";
    centerPosition: Point;
    extraIcons?: number | null;
    planetRadius?: number | null;
  };
  contrastColor?: string;
  flavourText?: string | null;
  source: string;
  spaceCannonDieCount?: number;
  spaceCannonHitsOn?: number;
  searchTags?: string[];
};

/** Etapy setupu startowego gry (backend: ``SetupStage``, RULES.md 45). */
export type GameSetupStage = "SECRETS" | "CUSTODIANS" | "OBJECTIVES";

export type GameSetupPlayer = {
  id: string;
  name: string;
  color: string | null;
  faction: string | null;
  isBot: boolean;
  /** Czy gracz już zatrzymał swój tajny cel. */
  chosen: boolean;
};

export type GameSetup = {
  stage: GameSetupStage;
  speakerId: string | null;
  /** Gracz wybierający teraz tajny cel (etap SECRETS; kolejka jednego ekranu). */
  chooserId: string | null;
  /** Kto jeszcze nie zatrzymał tajnego celu (jawne; w sieci wybierają naraz). */
  pending: string[];
  /** Gra sieciowa: wybór równoczesny, każdy widzi tylko swoich kandydatów (RULES.md 45.3). */
  simultaneous: boolean;
  /** Do kogo należą `candidates` (null = do nikogo / ukryte). */
  candidatesFor: string | null;
  players: GameSetupPlayer[];
  /** Dwa dobrane tajne cele gracza `candidatesFor` (puste dla pozostałych etapów). */
  candidates: string[];
  custodiansPlaced: boolean;
  /** Zakryte cele publiczne w taliach I i II etapu. */
  stage1Hidden: number;
  stage2Hidden: number;
};

export type Objective = {
  key: string;
  name: string;
  pointValue: number;
  revealed: boolean;
  scoredFactions: string[];
  peekingFactions: string[];
  multiScoring: boolean;
  hasRedTape: boolean;
  progressThreshold: number;
  factionProgress: Record<string, number>;
};

export type Objectives = {
  stage1Objectives: Objective[];
  stage2Objectives: Objective[];
  customObjectives: Objective[];
  allObjectives: Objective[];
};

export type Agenda = {
  alias: string;
  name: string;
  type: string;
  target: string;
  text1: string;
  text2?: string;
  category?: string;
  categoryDescription?: string;
  source:
    | "pok"
    | "base"
    | "absol"
    | "mahact"
    | "ignis_aurora"
    | "byz_agendas"
    | "voices_of_the_council"
    | "little_omega"
    | "miltymod"
    | "project_pi"
    | "sigma"
    | "omega_phase"
    | "riftset"
    | "blue_reverie"
    | "twilights_fall";
  forEmoji?: string;
  againstEmoji?: string;
  mapText?: string;
};

export type Ability = {
  id: string;
  name: string;
  faction: string;
  window?: string;
  windowEffect?: string;
  permanentEffect?: string;
  source: string;
  shortName?: string;
  homebrewReplacesID?: string;
};

export type PromissoryNote = {
  alias: string;
  name: string;
  color?: string;
  faction?: string;
  playArea: boolean;
  playImmediately?: boolean;
  source: string;
  text: string;
  shortName?: string;
  shrinkName?: boolean;
  attachment?: string | boolean;
  homebrewReplacesID?: string;
};

type ObjectiveDefinition = {
  alias: string;
  name: string;
  phase: string;
  text: string;
  points: number;
  source: string;
  homebrewReplacesID?: string;
};

export type SecretObjective = ObjectiveDefinition;

export type PublicObjective = ObjectiveDefinition;

export type Color = {
  alias: string;
  name: string;
  displayName?: string;
  aliases: string[];
  textColor: string;
  primaryColor?: RGBColor;
  secondaryColor?: RGBColor;
  primaryColorRef?: string;
  secondaryColorRef?: string;
  hue?: string;
};

export type Exploration = {
  id: string;
  type?: string;
  resolution?: string;
  attachmentId?: string;
  flavorText?: string;
  name: string;
  text: string;
  source: string;
};

export type AttachmentData = {
  id: string;
  name?: string;
  imagePath: string;
  techSpeciality?: string[];
  resourcesModifier?: number;
  influenceModifier?: number;
  token?: string;
  isLegendary?: boolean;
  isFakeAttachment?: boolean;
  planetTypes?: string[];
  spaceCannonHitsOn?: number;
  spaceCannonDieCount?: number;
  source: string;
};

export type ActionCard = {
  alias: string;
  name: string;
  phase: string;
  window: string;
  text: string;
  automationID?: string;
  actual_source?: string;
  flavorText?: string;
  source: string;
};

export type StrategyCardDefinition = {
  id: string;
  initiative: number;
  name: string;
  primaryTexts: string[];
  secondaryTexts: string[];
  imageFileName?: string;
  colourHexCode?: string;
  source: string;
  imageURL: string;
};

/** Jawne odsłonięcie reliktu (RULES.md 59.8); `relicId` null = talia była pusta. */
export type RelicReveal = {
  seq: number;
  /** `player_id` (`discordId`) zdobywającego. */
  playerId: string;
  relicId: string | null;
  source: "fragments" | "fracture" | "explore" | "deck";
  /** Purge'owane fragmenty (źródło `fragments`). */
  fragments?: string[];
  kind?: string;
  /** Planeta The Fracture (źródło `fracture`). */
  planet?: string;
  /** Karta eksploracji (źródło `explore`). */
  card?: string;
};

/** Efekt trwały w grze (``gameState.activeEffects``), opisany przez silnik z assetów. */
export type ActiveEffectData = {
  id: string;
  /** Klucz źródła (``leaders:letnevhero``) — do powiązania z wpisami historii. */
  key: string;
  name: string;
  /** Rodzaj komponentu: „Hero”, „Agent”, „Technology”... (pusty, gdy nieznany). */
  kind: string;
  text: string;
  /** Klucz tożsamości gracza (jak ``PlayerData.faction``); null = dotyczy wszystkich. */
  owner: string | null;
  scope: string;
  /** Do kiedy działa, np. „this game round”. */
  until: string;
  /** Czego dotyczy (np. statek, system); pusty, gdy nic. */
  detail: string;
  round: number;
};
