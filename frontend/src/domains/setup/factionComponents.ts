// Specjalne KOMPONENTY frakcji — fizyczne elementy gry (żetony i karty), które mają TYLKO
// wybrane frakcje i które odbiegają od zestawu wspólnego (żetony dowodzenia, jednostki,
// karty zdolności). Pokazujemy je w sekcji „Faction components" podglądu frakcji:
// ikona + liczba sztuk + nazwa, żeby gracz od razu widział, czym frakcja dysponuje.
//
// ZAKRES: tylko komponenty NIEBĘDĄCE jednostką/planetą — te (Avernus, Custodia Vigilia,
// Corsair, Eidolon Maximum) mają osobną sekcję „Breakthrough component"
// (``breakthroughComponents.ts``). Wspólne komponenty gry (np. ingress tokeny Fracture,
// frontier) NIE należą do frakcji, więc ich tu nie ma.
//
// ŹRÓDŁA liczb (nie z pamięci — patrz steering projektu):
//   • TI Wiki „Faction Specific Components" — lista komponentów per frakcja (Creuss: Alpha/
//     Beta/Gamma; Naalu: „0"; Nekro: X/Y; Empyrean: Void Tether; Titans: Sleepers; Cabal:
//     Dimensional Tear; Crimson: Breach; Deepwrought: Ocean; Firmament/Obsidian: Plots;
//     Bastion: Galvanize).
//   • Liczności z bota AsyncTI4 (TI4_map_generator_bot, ``WebPlayerArea.java`` /
//     ``PlayerAreaGenerator.java``): Sleepers 5, Breach 7, Galvanize 7, Alpha/Beta/Gamma po 1,
//     Sever 1; ``VoidTetherService`` dopuszcza nowy token tylko gdy na planszy jest < 2 → 2.
//   • Karty: 5 Plot cards (``assets/data/genericcards/firmament_plots.json``) i 5 Ocean cards
//     (``assets/data/planets/ocean1..5.json``) — liczone z danych.
//
// ⚠️ ZAŁOŻENIA (bez twardego źródła fizycznej liczby; do potwierdzenia przez użytkownika):
//   • Valefar „Z" ×7 — AsyncTI4 pokazuje maks. 7 (jeden na flagowiec innej frakcji).
//   • Dimensional Tear ×3 — jeden na każdy z 3 doków Cabal (żeton kładziony pod dokiem).

/** Jeden specjalny komponent frakcji. */
export interface FactionComponent {
  /** Stabilny identyfikator (klucz Reacta). */
  id: string;
  /** Nazwa wyświetlana (angielska — jak na komponencie w grze). */
  name: string;
  /** Liczba sztuk komponentu w pudełku frakcji. */
  count: number;
  /** Opis roli komponentu (sekcja „Role" karty szczegółów). */
  description: string;
  /** Rodzaj komponentu w podpisie karty (domyślnie „Faction component"). */
  kind?: string;
  /** Ukrywa pigułkę z liczbą (dla pojedynczych, nazwanych kart — np. plotów). */
  hideCount?: boolean;
  /**
   * Ikona: ścieżka logiczna grafiki (rozwiązywana `assetUrl`), `{ card: true }` = ikona
   * karty (brak grafiki karty w assetach) albo `{ glyph }` = krótki znak rysowany w kółku.
   */
  icon: string | { card: true } | { glyph: string };
}

const SLEEPER: FactionComponent = {
  id: "sleeper",
  name: "Sleeper tokens",
  count: 5,
  description:
    "Placed on planets with Terragenesis; Awaken turns a sleeper into a PDS.",
  icon: "/tokens/token_sleeper.png",
};

/** Karty Plot — teksty 1:1 z ``assets/data/genericcards/firmament_plots.json``. */
const PLOT_CARDS: FactionComponent[] = [
  {
    id: "plot-enervate",
    name: "Enervate",
    count: 1,
    kind: "Plot card",
    hideCount: true,
    description:
      "You can perform the secondary abilities of the puppeted player's strategy cards without spending command tokens; for \"Leadership,\" you can perform the primary ability instead.",
    icon: { card: true },
  },
  {
    id: "plot-siphon",
    name: "Siphon",
    count: 1,
    kind: "Plot card",
    hideCount: true,
    description:
      "When the puppeted player gains commodities, you gain an equal number of trade goods.",
    icon: { card: true },
  },
  {
    id: "plot-seethe",
    name: "Seethe",
    count: 1,
    kind: "Plot card",
    hideCount: true,
    description:
      "When this card is revealed, destroy all units on a non-home planet controlled by the puppeted player.\nAt the start of the status phase, destroy 1 of the puppeted player's infantry in any system.",
    icon: { card: true },
  },
  {
    id: "plot-assail",
    name: "Assail",
    count: 1,
    kind: "Plot card",
    hideCount: true,
    description:
      "Apply +1 to the results of each of your combat and unit ability rolls against the puppeted player.",
    icon: { card: true },
  },
  {
    id: "plot-extract",
    name: "Extract",
    count: 1,
    kind: "Plot card",
    hideCount: true,
    description:
      "When this card is revealed, gain 1 non-faction technology owned by the puppeted player.\nWhen the puppeted player gains a non-faction technology, you may spend 4 resources to gain that technology.",
    icon: { card: true },
  },
];

/** Pomocnik: karta Plot Black Spectrum (jak PLOT_CARDS, tylko inny tekst). */
function bspPlot(id: string, name: string, description: string): FactionComponent {
  return {
    id: `plot-${id}`,
    name,
    count: 1,
    kind: "Plot card",
    hideCount: true,
    description,
    icon: { card: true },
  };
}

/**
 * Karty Plot wariantu Black Spectrum (fanowskie) — teksty 1:1 z
 * ``assets/data/genericcards/black_spectrum_firmament_plots.json``. Zastępują
 * ``PLOT_CARDS`` (te same nazwy: pole ``homebrewReplacesID``), gdy w Ustawieniach
 * włączono „Black Spectrum Firmament Plots".
 */
const BSP_PLOT_CARDS: FactionComponent[] = [
  bspPlot(
    "enervate",
    "Enervate",
    "After this card is revealed, perform a strategic action using the puppeted player's readied strategy card; exhaust that strategy card. Then, each other player may resolve its secondary ability.\nWhen the puppeted player performs a strategic action, you can perform the secondary ability of their strategy card without spending a command token. For Leadership, you can perform the primary ability instead.",
  ),
  bspPlot(
    "siphon",
    "Siphon",
    "When this card is revealed, take 1 of the puppeted player's relics.\nWhen the puppeted player gains commodities, you gain an equal number of trade goods.",
  ),
  bspPlot(
    "seethe",
    "Seethe",
    "When this card is revealed, capture each unit on a non-home planet controlled by the puppeted player.\nOnce per combat in which you are the defender, after 1 of the puppeted player's non-structure units is destroyed, you may capture that unit.\nAt the start of the status phase, you may return 1 or more captured units of the puppeted player. Then, for each returned unit, place 1 unit of that type from your reinforcements in a system that contains your units and no other players' units.",
  ),
  bspPlot(
    "assail",
    "Assail",
    "When this card is revealed, choose 1 non-fighter ship type that the puppeted player has on the game board. The puppeted player destroys half of their ships of that type, rounded up.\nApply +1 to the results of each of your combat and unit ability rolls against the puppeted player.\nAt the start of your turn, you may treat your flagship as if it had the text ability of 1 of the puppeted players' flagship until the end of that turn.",
  ),
  bspPlot(
    "extract",
    "Extract",
    "When this card is revealed, choose 1 non-unit upgrade, non-faction technology owned by the puppeted player; that player returns that technology to their technology deck. Then, gain that technology, if able.\nWhen the puppeted player gains a non-faction technology, you may spend 4 resources to gain that technology.",
  ),
];

/** Aktualny zestaw kart Plot (standardowy albo Black Spectrum). */
export function plotCardSet(blackSpectrum: boolean): FactionComponent[] {
  return blackSpectrum ? BSP_PLOT_CARDS : PLOT_CARDS;
}

/** Opis efektu karty Plot po nazwie/aliasie (np. „seethe"); undefined, gdy nieznana. */
export function plotCardDescription(
  alias: string | null | undefined,
  blackSpectrum: boolean,
): string | undefined {
  if (!alias) return undefined;
  const key = alias.toLowerCase();
  return plotCardSet(blackSpectrum).find((c) => c.name.toLowerCase() === key)
    ?.description;
}

/** Mapa: id frakcji → jej specjalne komponenty (tylko frakcje, które jakieś mają). */
const FACTION_COMPONENTS: Record<string, FactionComponent[]> = {
  ghost: [
    {
      id: "creussalpha",
      name: "Alpha wormhole token",
      count: 1,
      description: "Creates an alpha wormhole in the system where it is placed.",
      icon: "/tokens/token_creussalpha.png",
    },
    {
      id: "creussbeta",
      name: "Beta wormhole token",
      count: 1,
      description: "Creates a beta wormhole in the system where it is placed.",
      icon: "/tokens/token_creussbeta.png",
    },
    {
      id: "creussgamma",
      name: "Gamma wormhole token",
      count: 1,
      description: "Creates a gamma wormhole in the system where it is placed.",
      icon: "/tokens/token_creussgamma.png",
    },
  ],
  naalu: [
    {
      id: "naalu0",
      name: "“0” token",
      count: 1,
      description:
        "Placed on your chosen strategy card: you are first in initiative order.",
      icon: { glyph: "0" },
    },
  ],
  nekro: [
    {
      id: "valefarx",
      name: "“X” assimilator token",
      count: 1,
      description: "Tracks which faction technology Valefar Assimilator X is copying.",
      icon: "/extra/marker_valefarX.png",
    },
    {
      id: "valefary",
      name: "“Y” assimilator token",
      count: 1,
      description: "Tracks which faction technology Valefar Assimilator Y is copying.",
      icon: "/extra/marker_valefarY.png",
    },
    {
      id: "valefarz",
      name: "“Z” assimilator tokens",
      count: 7,
      description:
        "Breakthrough: placed on another player's faction sheet to copy their flagship abilities.",
      icon: "/extra/marker_valefarZ.png",
    },
  ],
  empyrean: [
    {
      id: "voidtether",
      name: "Void Tether tokens",
      count: 2,
      description:
        "Breakthrough: placed on a system border; other players treat those systems as not adjacent.",
      icon: "/borders/void_tether.png",
    },
  ],
  titans: [SLEEPER],
  cabal: [
    {
      id: "dimensionaltear",
      name: "Dimensional Tear tokens",
      count: 3,
      description:
        "Placed under a space dock to mark that its system is a gravity rift.",
      icon: "/decals/DimensionalTear.png",
    },
  ],
  crimson: [
    {
      id: "breach",
      name: "Breach tokens",
      count: 7,
      description: "Placed in systems as active or inactive breaches (Incursion).",
      icon: "/tokens/token_breachActive.png",
    },
    {
      id: "sever",
      name: "Sever token",
      count: 1,
      description:
        "Promissory note token: wormholes in its system have no effect during movement.",
      icon: "/tokens/token_severed.png",
    },
  ],
  bastion: [
    {
      id: "galvanize",
      name: "Galvanize tokens",
      count: 7,
      description: "Mark units that are galvanized (Galvanize ability).",
      icon: "/extra/marker_galvanize.png",
    },
  ],
  firmament: PLOT_CARDS,
  obsidian: PLOT_CARDS,
};

/** Specjalne komponenty frakcji o danym id (pusta lista, gdy frakcja nie ma żadnych). */
export function factionComponents(
  factionId: string | null | undefined,
  blackSpectrumPlots = false,
): FactionComponent[] {
  if (!factionId) return [];
  // Firmament/Obsidian: ploty zależne od wariantu (Ustawienia → Game variants).
  if (factionId === "firmament" || factionId === "obsidian") {
    return plotCardSet(blackSpectrumPlots);
  }
  return FACTION_COMPONENTS[factionId] ?? [];
}

/**
 * Komponenty frakcji będące KARTAMI PLANET (Deepwrought: 5 kart Ocean, każda 1/1) —
 * renderowane jak planety (klikalna karta planety); id z danych planet.
 */
const FACTION_COMPONENT_PLANETS: Record<string, string[]> = {
  deepwrought: ["ocean1", "ocean2", "ocean3", "ocean4", "ocean5"],
};

/** Id kart planet będących komponentami frakcji (pusta lista, gdy brak). */
export function factionComponentPlanets(
  factionId: string | null | undefined,
): string[] {
  if (!factionId) return [];
  return FACTION_COMPONENT_PLANETS[factionId] ?? [];
}
