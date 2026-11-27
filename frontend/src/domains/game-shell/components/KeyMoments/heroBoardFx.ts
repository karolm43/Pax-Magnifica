/**
 * Efekty bohaterów NA PLANSZY (RULES.md 64.4) — po scenie bohatera mapa „reaguje” na jego
 * zdolność. Dane (który bohater -> jaki przepis) + czyste wyliczenie celów z kafelków mapy.
 * Rysuje `HeroBoardFxLayer` (warstwa w treści mapy, więc idzie za przesuwaniem i zoomem).
 * Nowy bohater w silniku => dopisz przepis tutaj (inaczej zostaje sama scena). Każdy bohater
 * ma WŁASNY znacznik pasujący do frakcji i zdolności — nie generyczny pierścień.
 */
import { create } from "zustand";
import type { Tile } from "@/entities/game/types";
import type { SoundName, SoundOpts } from "@/domains/battle/battleSound";
import type { HeroArea, ReplacedTile } from "./keyMoments";

/** Gdzie na planszy dzieje się efekt. */
export type FxTarget =
  | "ground" // systemy z siłami naziemnymi bohatera
  | "defense" // systemy z PDS albo mechami bohatera (obrona planet)
  | "ships" // systemy ze statkami bohatera
  | "units" // systemy z dowolnymi jednostkami bohatera
  | "active" // aktywny system (produkcja / walka / inwazja), inaczej „units”
  | "mecatol" // Mecatol Rex
  | "nova" // kafel supernowej Muaat (Nova Seed) — po wymianie kafla
  | "docks" // systemy z dokami bohatera (Dimensional Tear Cabal, przekaźnik Saar)
  | "planet" // system planety, do której bohater dołączył kartę (Geoform -> Elysium)
  | "destroyed" // system planety zniszczonej przez Stellar Converter (`tile.destroyedPlanets`)
  | "swapped" // both systems whose tiles swapped places (Singularity Reactor, `run.replaced`)
  | "token" // system where a Creuss wormhole token opened (`area` "gain" of the moment)
  | "border"; // both systems of a Void Tether border (`area` "gain" of the moment, RULES.md 62.20)

/** Wygląd efektu w systemie docelowym (każdy bohater ma własny, pasujący do frakcji). */
export type FxMark =
  | "bloom" // Arborec: pnącza i zarodniki
  | "beam" // Sol: orbitalne słupy światła
  | "coins" // Hacan: deszcz trade goods
  | "slash" // Sardakk N'orr: szpony
  | "crown" // Winnu: korona imperium i promienie
  | "forge" // Naaz-Rokha: kuźnia reliktu
  | "aegis" // Xxcha: kopuła tarczy
  | "nova" // Muaat: supernowa
  | "reticle" // Letnev: namierzanie floty
  | "circuit" // Jol-Nar: ścieżki obwodu i węzły danych
  | "grapple" // Mentak: haki abordażowe
  | "helix" // Argent Flight: podwójna spirala skrzydeł
  | "drop" // Yin: kapsuły z piechotą-klonami
  | "warp" // L1Z1X: wyjście z ciemnej przestrzeni (siatka materializacji)
  | "blast" // Saar: fala Armageddon Relay
  | "psi" // Naalu: fale psioniczne i oko
  | "maw" // Cabal: wir Event Horizon wciągający sąsiednie systemy
  | "awaken" // Titans: przebudzenie Elysium
  | "converter" // Stellar Converter: okręty z BOMBARDMENT rozbijają planetę
  | "rift" // Creuss: two wormhole vortices joined by a tether, the tiles fly to trade places
  | "portal" // Creuss wormhole token: a vortex opens (and the old one collapses when moved)
  | "voideye" // Empyrean: frontier sigils condense from the void, an eye opens where it explores
  | "tether" // Empyrean Void Tether: a dark seam seals the border, the two systems recoil
  | "timewarp" // Nomad: a chronometer rewinds over the flagship, chrono-locks open on its tokens
  | "keyhole"; // Yssaril: shadows creep over rival homes, a keyhole is slashed open, a card is lifted

export type HeroFxRecipe = {
  /** Przyciemnienie całej planszy (0–1). */
  dim?: number;
  /** Fala przez całą planszę: skan (lewa -> prawa), świt, zakłócenia obrazu, mgła. */
  sweep?: "scan" | "dawn" | "static" | "mist";
  /** Cienie statków przepływające nad planszą (typy jednostek AsyncTI4). */
  shadows?: string[];
  target: FxTarget;
  mark: FxMark;
  /** Kolor efektu (rgb), domyślnie kolor gracza. */
  tone?: string;
  /** Czas efektu (ms). */
  ms: number;
  /** Dźwięki efektu (ms od startu, próbki walki — `battleSound`; `rate`/`reverse` jak tam). */
  sounds?: ({ at: number; name: SoundName } & SoundOpts)[];
  /** Błysk całej planszy (ms od startu). */
  flashAt?: number;
  /** Chwila (ms), w której wymieniony kafel odsłania nowy (pod błyskiem); domyślnie od razu. */
  revealAt?: number;
  /** Wstrząsy planszy: chwila (ms od startu), siła (px), czas (ms). */
  quake?: { at: number; px: number; ms: number }[];
  /**
   * Miejsce zdolności z faktów `area` wpisu (np. Sol: systemy, z których zniknęły jego żetony);
   * `target` zostaje zapasem, gdy wpis takich faktów nie ma.
   */
  area?: { self: boolean; kinds: HeroArea["kind"][] };
};

/** Bohaterowie zaimplementowani w silniku (`core/hooks/factions/*`). */
export const HERO_BOARD_FX: Record<string, HeroFxRecipe> = {
  // Void Transference: brak limitu floty — plansza ciemnieje pod cieniami okrętów, a nad
  // flotami Letnev zaciskają się czerwone celowniki baronii.
  letnevhero: {
    dim: 0.6,
    shadows: ["dn", "fs", "dn", "ca", "dn"],
    target: "ships",
    mark: "reticle",
    tone: "255 70 60",
    ms: 5200,
    sounds: [
      { at: 0, name: "fleetEnter", gain: 0.7, rate: 0.7 },
      { at: 1400, name: "arriveHeavy", gain: 0.6, rate: 0.8 },
    ],
  },
  // Overgrowth: produkcja wszędzie, gdzie są siły naziemne — zieleń i zarodniki wyrastają z planet.
  arborechero: {
    dim: 0.25,
    area: { self: true, kinds: ["gain"] },
    target: "ground",
    mark: "bloom",
    tone: "120 230 110",
    ms: 4400,
    sounds: [{ at: 200, name: "fleetEnter", gain: 0.35, rate: 0.5 }],
  },
  // Twilight Directive: żetony dowodzenia Sol wracają z planszy — złota fala zmierzchu, a z każdego
  // systemu, z którego zniknął żeton, w niebo unosi się słup światła z żetonem.
  solhero: {
    dim: 0.3,
    sweep: "dawn",
    area: { self: true, kinds: ["token_removed"] },
    target: "units",
    mark: "beam",
    tone: "255 205 90",
    ms: 4400,
    sounds: [{ at: 600, name: "sunfire", gain: 0.35, rate: 0.8 }],
  },
  // Brilliance of the Hylar: wymiana technologii — skan danych i obwody rozrastające się
  // po systemach Jol-Nar.
  jolnarhero: {
    dim: 0.35,
    sweep: "scan",
    target: "units",
    mark: "circuit",
    tone: "90 180 255",
    ms: 4400,
    sounds: [
      { at: 200, name: "laser", gain: 0.35, rate: 1.6 },
      { at: 900, name: "plasma", gain: 0.3, rate: 1.4 },
    ],
  },
  // Sanction of the Quieron: darmowa produkcja — szlaki handlowe zbiegają się do systemu,
  // karawany niosą towar, deszcz trade goods i wielka moneta Quieron nad produkcją.
  hacanhero: {
    dim: 0.3,
    target: "active",
    mark: "coins",
    tone: "255 200 70",
    ms: 4600,
    sounds: [
      { at: 0, name: "fleetEnter", gain: 0.35, rate: 1.4 },
      { at: 1300, name: "diceThrow", gain: 0.5, rate: 1.3 },
      { at: 1900, name: "diceThrow", gain: 0.4, rate: 1.5 },
      { at: 2500, name: "sustain", gain: 0.4, rate: 1.5 },
    ],
  },
  // Sleeper Cell: zniszczone statki wroga wracają jako Mentak — haki abordażowe wbijają się
  // w system walki i ściągają łup.
  mentakhero: {
    dim: 0.4,
    target: "active",
    mark: "grapple",
    tone: "255 140 60",
    ms: 4200,
    sounds: [
      { at: 300, name: "missile", gain: 0.5, rate: 1.2 },
      { at: 900, name: "impact", gain: 0.6 },
      { at: 1100, name: "impact", gain: 0.5, rate: 0.8 },
    ],
  },
  // Brood Swarm: prosto do lądowania — rój N'orr nurkuje w system inwazji, szpony tną planetę
  // i zostaje żarząca się rana.
  sardakkhero: {
    dim: 0.35,
    target: "active",
    mark: "slash",
    tone: "255 60 50",
    ms: 4200,
    quake: [{ at: 1500, px: 5, ms: 500 }],
    sounds: [
      { at: 0, name: "fleetEnter", gain: 0.5, rate: 1.6 },
      { at: 700, name: "dropPod", gain: 0.5, rate: 1.3 },
      { at: 1500, name: "impact", gain: 0.7, rate: 1.3 },
      { at: 1620, name: "impact", gain: 0.6, rate: 1.1 },
      { at: 1740, name: "groundBlast", gain: 0.7 },
    ],
  },
  // Sins of the Father: primary dowolnej karty strategii — korona dawnego imperium stempluje
  // Mecatol Rex, laur się zamyka, a promienie władzy rozchodzą się przez całą planszę.
  winnuhero: {
    dim: 0.35,
    target: "mecatol",
    mark: "crown",
    tone: "255 210 90",
    ms: 4800,
    sweep: "dawn",
    sounds: [
      { at: 300, name: "arriveHeavy", gain: 0.7, rate: 0.6 },
      { at: 1200, name: "sunfire", gain: 0.3, rate: 0.7 },
    ],
  },
  // Planetary Defense Nexus - Aegis: PDS i mechy na planetach — kopuły tarcz wznoszą się nad nimi.
  "xxchahero-te": {
    dim: 0.3,
    area: { self: true, kinds: ["gain"] },
    target: "defense",
    mark: "aegis",
    tone: "110 230 190",
    ms: 4400,
    sounds: [{ at: 300, name: "sustain", gain: 0.5, rate: 0.8 }],
  },
  // Helix Protocol: skrzydła Argent przeskakują do systemów z żetonami — cienie niszczycieli
  // i podwójna spirala nad flotami.
  argenthero: {
    dim: 0.4,
    shadows: ["dd", "dd", "fs", "dd"],
    area: { self: true, kinds: ["gain"] },
    target: "ships",
    mark: "helix",
    tone: "255 150 60",
    ms: 4600,
    sounds: [
      { at: 0, name: "fleetEnter", gain: 0.6, rate: 1.2 },
      { at: 1300, name: "arrive", gain: 0.5 },
    ],
  },
  // Quantum Dissemination: piechota z rezerwy spada na planety — klony w kapsułach.
  yinhero: {
    dim: 0.4,
    sweep: "mist",
    area: { self: true, kinds: ["gain"] },
    target: "ground",
    mark: "drop",
    tone: "235 235 245",
    ms: 4400,
    sounds: [
      { at: 300, name: "dropPod", gain: 0.6 },
      { at: 1050, name: "podLand", gain: 0.6 },
    ],
  },
  // Dark Space Navigation: flagowiec i pancerniki wychodzą z mroku — zakłócony obraz, siatka
  // materializacji i cienie okrętów.
  l1z1xhero: {
    dim: 0.55,
    sweep: "static",
    shadows: ["dn", "fs", "dn"],
    area: { self: true, kinds: ["gain"] },
    target: "ships",
    mark: "warp",
    tone: "210 60 60",
    ms: 4600,
    sounds: [
      { at: 0, name: "warSunEnter", gain: 0.5, rate: 1.3 },
      { at: 1200, name: "arriveHeavy", gain: 0.7 },
    ],
  },
  // Armageddon Relay: fala uderzeniowa i odłamki w wybranym systemie przy doku Saar (tam, gdzie
  // zginęła piechota i myśliwce rywali); bez strat — w systemach z dokami.
  saarhero: {
    dim: 0.45,
    area: { self: false, kinds: ["loss"] },
    target: "docks",
    mark: "blast",
    tone: "230 150 60",
    ms: 4400,
    quake: [{ at: 700, px: 6, ms: 700 }],
    sounds: [
      { at: 200, name: "missile", gain: 0.5, rate: 0.8 },
      { at: 700, name: "explosionHeavy", gain: 0.8, rate: 0.8 },
    ],
  },
  // Perfect Synthesis: Forge Legend — skan archeologów, runiczne pierścienie zgrywają się,
  // z kuźni tryskają iskry, wznosi się kryształ reliktu i rozkładają dwie karty strategii.
  naazhero: {
    dim: 0.35,
    sweep: "scan",
    target: "units",
    mark: "forge",
    tone: "110 220 160",
    ms: 4800,
    sounds: [
      { at: 300, name: "mechStep", gain: 0.6, rate: 1.2 },
      { at: 1300, name: "assaultCannon", gain: 0.45, rate: 1.4 },
      { at: 1500, name: "sustain", gain: 0.5, rate: 1.3 },
    ],
  },
  // C-Radium Geometry: Poison of the Nefishh - umysły rywali oddają notki; fioletowa mgła,
  // psioniczne oko i fale nad systemami Naalu.
  naaluhero: {
    dim: 0.5,
    sweep: "mist",
    target: "units",
    mark: "psi",
    tone: "185 120 255",
    ms: 4600,
    sounds: [
      { at: 0, name: "warSunEnter", gain: 0.35, rate: 1.6 },
      { at: 900, name: "sustain", gain: 0.4, rate: 0.6 },
    ],
  },
  // Dimensional Anchor: Event Horizon — z każdego doku Cabal (Dimensional Tear) otwiera się
  // wir, macki sięgają do SĄSIEDNICH systemów i wciągają ich okręty; plansza tonie w mroku i drży.
  cabalhero: {
    dim: 0.7,
    target: "docks",
    mark: "maw",
    tone: "200 30 70",
    ms: 6000,
    quake: [
      { at: 400, px: 3, ms: 900 },
      { at: 2600, px: 5, ms: 700 },
    ],
    sounds: [
      { at: 0, name: "warSunEnter", gain: 0.7, rate: 0.45 },
      { at: 900, name: "explosionHeavy", gain: 0.6, rate: 0.5, reverse: true, endIn: 1700 },
      { at: 2600, name: "arriveHeavy", gain: 0.9, rate: 0.6 },
    ],
  },
  // Geoform: Elysium budzi się jako tytan — plansza drży, z planety wychodzą szczeliny magmy,
  // rdzeń tytana wznosi się w pancernych płytach, a trzy strzały SPACE CANNON 5 (x3) mkną w niebo.
  titanshero: {
    dim: 0.5,
    target: "planet",
    mark: "awaken",
    tone: "255 110 170",
    ms: 6200,
    quake: [
      { at: 0, px: 3, ms: 1300 },
      { at: 1500, px: 7, ms: 800 },
    ],
    sounds: [
      { at: 0, name: "mechStep", gain: 0.8, rate: 0.5 },
      { at: 700, name: "mechStep", gain: 0.9, rate: 0.45 },
      { at: 1500, name: "explosionHeavy", gain: 0.7, rate: 0.55 },
      { at: 2900, name: "assaultCannon", gain: 0.6 },
      { at: 3250, name: "assaultCannon", gain: 0.55, rate: 1.1 },
      { at: 3600, name: "assaultCannon", gain: 0.5, rate: 1.2 },
    ],
  },
  // Singularity Reactor: the board darkens, both systems tear open into counter-rotating
  // wormhole vortices joined by an azure tether; the old tiles lift, fold and fly along the arc
  // to trade places; under the flash the swapped board is revealed, the vortices collapse in
  // ripples. Sound: a low wormhole hum, a reversed rush (space folding), the snap, settling.
  ghosthero: {
    dim: 0.45,
    target: "swapped",
    mark: "rift",
    tone: "110 190 255",
    ms: 7600,
    flashAt: 4200,
    revealAt: 4250,
    quake: [
      { at: 1300, px: 2, ms: 1400 },
      { at: 4200, px: 7, ms: 900 },
    ],
    sounds: [
      { at: 0, name: "warSunEnter", gain: 0.6, rate: 0.5 },
      { at: 900, name: "laser", gain: 0.35, rate: 0.45 },
      { at: 1500, name: "explosionHeavy", gain: 0.7, rate: 0.7, reverse: true, endIn: 2600 },
      { at: 2400, name: "fleetEnter", gain: 0.45, rate: 0.6 },
      { at: 4200, name: "explosionHeavy", gain: 0.95, rate: 0.55 },
      { at: 4260, name: "sunfire", gain: 0.55, rate: 0.6 },
      { at: 4900, name: "arriveHeavy", gain: 0.7, rate: 0.7 },
      { at: 5600, name: "warSunEnter", gain: 0.3, rate: 0.7 },
    ],
  },
  // Multiverse Shift — Opening the Eye (Conservator Procyon, RULES.md 62.20): the board sinks into
  // the void (heavy dim + drifting mist); in every planetless system a frontier sigil condenses
  // out of the dark and the token drops in; where the Empyrean have ships an eye opens over it,
  // flares (flash) and gazes into the token - the exploration - then closes. Sound: a deep void
  // hum, a reversed rush as the eyes open, the flare, a fading low tone.
  empyreanhero: {
    dim: 0.62,
    sweep: "mist",
    area: { self: true, kinds: ["frontier", "explore"] },
    target: "ships",
    mark: "voideye",
    tone: "170 110 255",
    ms: 7000,
    flashAt: 3700,
    quake: [{ at: 3700, px: 3, ms: 700 }],
    sounds: [
      { at: 0, name: "warSunEnter", gain: 0.55, rate: 0.42 },
      { at: 600, name: "fleetEnter", gain: 0.35, rate: 0.45 },
      { at: 2100, name: "explosionHeavy", gain: 0.55, rate: 0.5, reverse: true, endIn: 1600 },
      { at: 3700, name: "sunfire", gain: 0.5, rate: 0.45 },
      { at: 3760, name: "explosionHeavy", gain: 0.45, rate: 0.6 },
      { at: 5200, name: "warSunEnter", gain: 0.3, rate: 0.35 },
    ],
  },
  // Guild of Spies (Kyver, Blade and Key, RULES.md 62.22): the board sinks into jungle mist; over
  // EVERY rival's home system shadows and fronds close in, an eye slit opens in the dark and
  // settles into a glowing keyhole, a key slides in and turns; at the flash a blade slashes the
  // lock open, a card rises out of the cut and drifts away while torn shards scatter (the card
  // taken or the 3 random discards). Sound: a low creeping hum, the lock's clicks, the blade's
  // swish and a soft whoosh of the stolen card.
  yssarilhero: {
    dim: 0.65,
    sweep: "mist",
    area: { self: true, kinds: ["kyver"] },
    target: "units",
    mark: "keyhole",
    tone: "120 235 150",
    ms: 6800,
    flashAt: 3000,
    quake: [{ at: 3000, px: 2, ms: 300 }],
    sounds: [
      { at: 0, name: "fleetEnter", gain: 0.3, rate: 0.4 },
      { at: 900, name: "mechStep", gain: 0.3, rate: 1.7 },
      { at: 2000, name: "diceClack", gain: 0.45, rate: 0.5 },
      { at: 2300, name: "diceClack", gain: 0.4, rate: 0.42 },
      { at: 2950, name: "laser", gain: 0.45, rate: 1.6 },
      { at: 3000, name: "impact", gain: 0.3, rate: 1.4 },
      { at: 3300, name: "retreat", gain: 0.3, rate: 1.4 },
    ],
  },
  // Probability Matrix: Time Warp (Ahk-Syl Siven, RULES.md 62.21): the board flickers like a
  // broken recording (static); over the flagship a chronometer unfolds, its hands spin backwards
  // ever faster while ghost hexes of other probabilities peel away; at the flash the dial bursts
  // into time ripples. Over every system with a Nomad command token an hourglass runs upward and
  // its chrono-lock splits open - the flagship may leave those systems this round. Sound: a low
  // temporal hum, a long reversed rush (time running back), the snap of the flash, a fading tick.
  nomadhero: {
    dim: 0.5,
    sweep: "static",
    area: { self: true, kinds: ["time_warp", "time_warp_token"] },
    target: "ships",
    mark: "timewarp",
    tone: "110 225 255",
    ms: 7200,
    flashAt: 3600,
    quake: [{ at: 3600, px: 4, ms: 800 }],
    sounds: [
      { at: 0, name: "warSunEnter", gain: 0.55, rate: 0.6 },
      { at: 700, name: "explosionHeavy", gain: 0.6, rate: 0.55, reverse: true, endIn: 2900 },
      { at: 1500, name: "laser", gain: 0.3, rate: 0.4, reverse: true },
      { at: 3600, name: "sunfire", gain: 0.55, rate: 0.7 },
      { at: 3650, name: "explosionHeavy", gain: 0.5, rate: 0.75 },
      { at: 4300, name: "armorHit", gain: 0.45, rate: 0.6 },
      { at: 5400, name: "diceClack", gain: 0.35, rate: 0.7 },
      { at: 5900, name: "diceClack", gain: 0.25, rate: 0.6 },
    ],
  },
  // Nova Seed: gwiazda systemu puchnie, korona zapada się w punkt, wybuch supernowej (błysk,
  // promienie dyfrakcyjne, rozszerzająca się powłoka gazu, ejekta), potem pulsująca mgławica.
  // Stary kafel znika pod błyskiem (revealAt); dźwięk niski: pomruk, wsysanie, głuchy huk.
  muaathero: {
    dim: 0.65,
    target: "nova",
    mark: "nova",
    tone: "255 130 50",
    ms: 9000,
    flashAt: 2850,
    revealAt: 3000,
    quake: [{ at: 2850, px: 6, ms: 900 }],
    sounds: [
      { at: 0, name: "warSunEnter", gain: 0.7, rate: 0.55 },
      { at: 400, name: "explosionHeavy", gain: 0.85, rate: 0.6, reverse: true, endIn: 2450 },
      { at: 2850, name: "explosionHeavy", gain: 1, rate: 0.5 },
      { at: 2950, name: "explosionHeavy", gain: 0.7, rate: 0.75 },
      { at: 3300, name: "sunfire", gain: 0.5, rate: 0.5 },
      { at: 4200, name: "warSunEnter", gain: 0.4, rate: 0.45 },
    ],
  },
};

/**
 * Efekty RELIKTÓW na planszy (bez sceny portretu — od razu mapa). Klucz = id reliktu.
 * Stellar Converter: inny styl niż Nova Seed (gorąca supernowa gwiazdy) — zimna, „techniczna”
 * energia: okręty z BOMBARDMENT ładują się, wiązki zbiegają się na planecie w sąsiednim systemie,
 * siatka pola otula planetę i ją ściska („concentrated”), skorupa pęka i planeta rozpada się
 * w pierścień odłamków („scattered”); pod błyskiem pojawia się żeton zniszczonej planety.
 */
export const RELIC_BOARD_FX: Record<string, HeroFxRecipe> = {
  stellarconverter: {
    dim: 0.6,
    target: "destroyed",
    mark: "converter",
    tone: "120 205 255",
    ms: 8200,
    flashAt: 3400,
    revealAt: 3450,
    quake: [
      { at: 2600, px: 2, ms: 800 },
      { at: 3400, px: 9, ms: 1000 },
    ],
    sounds: [
      { at: 0, name: "warSunEnter", gain: 0.55, rate: 1.35 },
      { at: 500, name: "assaultCannon", gain: 0.75, rate: 0.75 },
      { at: 1450, name: "sunfire", gain: 0.7, rate: 0.8 },
      { at: 1600, name: "laser", gain: 0.45, rate: 0.6 },
      { at: 2000, name: "explosionHeavy", gain: 0.8, rate: 0.7, reverse: true, endIn: 1400 },
      { at: 3400, name: "explosionHeavy", gain: 1, rate: 0.62 },
      { at: 3440, name: "groundBlast", gain: 0.9, rate: 0.55 },
      { at: 3700, name: "explosionHeavy", gain: 0.55, rate: 0.9 },
      { at: 4300, name: "impact", gain: 0.45, rate: 0.6 },
      { at: 4800, name: "impact", gain: 0.35, rate: 0.5 },
    ],
  },
};

/**
 * Creuss wormhole token placed or moved (Wormhole Generator, Creuss IFF, Icarus Drive) or the
 * Hil Colish carrying its delta wormhole to another system — a short
 * board effect for everybody, no portrait: a vortex in the token's colour opens in the new
 * system (and, when moved, the old one collapses). Key = token id (`assets/data/tokens`).
 */
const portal = (tone: string): HeroFxRecipe => ({
  dim: 0.18,
  target: "token",
  mark: "portal",
  tone,
  ms: 2800,
  area: { self: true, kinds: ["gain"] },
  sounds: [
    { at: 0, name: "warSunEnter", gain: 0.45, rate: 0.85 },
    { at: 650, name: "laser", gain: 0.25, rate: 0.5 },
    { at: 1150, name: "arrive", gain: 0.4, rate: 0.8 },
  ],
});
export const TOKEN_BOARD_FX: Record<string, HeroFxRecipe> = {
  creussalpha: portal("255 150 70"),
  creussbeta: portal("80 185 255"),
  creussgamma: portal("200 120 255"),
  // Hil Colish's delta wormhole moving with the flagship (`unit_wormhole` facts).
  whdelta: portal("80 235 205"),
};

/**
 * Empyrean Void Tether placed / moved onto a border (RULES.md 62.20) — no portrait: a seam of
 * darkness is drawn along the shared edge, chains of void lock it, both systems recoil from it
 * (other players no longer treat them as adjacent); a moved tether's old seam dissolves.
 */
export const TETHER_BOARD_FX: HeroFxRecipe = {
  dim: 0.22,
  target: "border",
  mark: "tether",
  tone: "170 110 255",
  ms: 3400,
  area: { self: true, kinds: ["gain"] },
  sounds: [
    { at: 0, name: "laser", gain: 0.3, rate: 0.35 },
    { at: 700, name: "warSunEnter", gain: 0.35, rate: 0.6 },
    { at: 1350, name: "armorHit", gain: 0.55, rate: 0.55 },
    { at: 1420, name: "impact", gain: 0.4, rate: 0.5 },
  ],
};

const GROUND = new Set(["gf", "mf"]);
const DEFENSE = new Set(["pd", "mf"]);
const DOCK = "sd";
const MECATOL_SYSTEM_IDS = new Set(["18", "112"]);
/** Kafel „Nova Seed” (supernowa Muaat, `assets/systems/81.json`) — jeden w grze. */
const NOVA_SEED_SYSTEM_ID = "81";
/** Odległość środków sąsiednich kafli (rozstaw siatki: 260 poziomo, 300 pionowo). */
const NEIGHBOR_DISTANCE = 300;

/** Jednostki gracza w kafelku (klucz `unitsByFaction` = frakcja; zapasowo kolor). */
function unitsOf(tile: Tile, keys: string[]) {
  const pick = (m: Record<string, { entityId: string; count: number }[]>) =>
    keys.flatMap((k) => m[k] ?? []);
  const space = pick(tile.unitsByFaction);
  const planets = Object.values(tile.planets).flatMap((p) => pick(p.unitsByFaction ?? {}));
  return { space, planets };
}

/** Właściciel efektu: frakcja/kolor (klucze jednostek), planety z karty i miejsca działania. */
export type FxOwner = {
  faction: string | null;
  color: string | null;
  planets?: string[];
  areas?: HeroArea[];
  /** Tiles the moment swapped (target "swapped"). */
  replaced?: ReplacedTile[];
};

/** Pozycje systemów, w których dzieje się efekt. */
export function fxTargets(
  recipe: HeroFxRecipe,
  tiles: Tile[],
  owner: FxOwner,
  activeSystem: string | null,
): string[] {
  const keys = [owner.faction, owner.color].filter((k): k is string => !!k);
  const pick = (test: (t: Tile) => boolean) => tiles.filter(test).map((t) => t.position);
  const has = (units: { entityId: string; count: number }[], ids: Set<string>) =>
    units.some((u) => ids.has(u.entityId) && u.count > 0);
  if (recipe.area && owner.areas?.length) {
    const { self, kinds } = recipe.area;
    const wanted = new Set(
      owner.areas.filter((a) => a.self === self && kinds.includes(a.kind)).map((a) => a.position),
    );
    const hit = pick((t) => wanted.has(t.position));
    if (hit.length > 0) return hit;
  }
  switch (recipe.target) {
    case "mecatol":
      return pick((t) => MECATOL_SYSTEM_IDS.has(t.systemId)).slice(0, 1);
    case "nova":
      return pick((t) => t.systemId === NOVA_SEED_SYSTEM_ID).slice(0, 1);
    case "planet": {
      const planets = new Set(owner.planets ?? []);
      return pick((t) => Object.keys(t.planets).some((p) => planets.has(p)));
    }
    case "swapped": {
      const swapped = new Set((owner.replaced ?? []).map((r) => r.position));
      return pick((t) => swapped.has(t.position));
    }
    case "border":
    case "token": {
      const opened = new Set(
        (owner.areas ?? []).filter((a) => a.kind === "gain").map((a) => a.position),
      );
      return pick((t) => opened.has(t.position));
    }
    case "destroyed": {
      const planets = new Set(owner.planets ?? []);
      return pick((t) => (t.destroyedPlanets ?? []).some((p) => planets.has(p)));
    }
    case "docks": {
      const docks = new Set([DOCK]);
      return pick((t) => {
        const u = unitsOf(t, keys);
        return has(u.space, docks) || has(u.planets, docks);
      });
    }
    case "active":
      if (activeSystem && tiles.some((t) => t.position === activeSystem)) return [activeSystem];
      return fxTargets({ ...recipe, target: "units" }, tiles, owner, null);
    case "ground":
      return pick((t) => has(unitsOf(t, keys).planets, GROUND));
    case "defense":
      return pick((t) => has(unitsOf(t, keys).planets, DEFENSE));
    case "ships":
      return pick((t) => unitsOf(t, keys).space.some((u) => !GROUND.has(u.entityId) && u.count > 0));
    case "units":
      return pick((t) => {
        const u = unitsOf(t, keys);
        return [...u.space, ...u.planets].some((x) => x.count > 0);
      });
  }
}

/**
 * Kafle sąsiednie (geometrycznie) do systemu — strefa „in or adjacent” Dimensional Anchor.
 * Tylko do wizualizacji: hiperlinie i wormhole liczy silnik, tu wystarcza siatka heksów.
 */
export function neighborTiles(tiles: Tile[], center: Tile): Tile[] {
  const { x, y } = center.properties;
  return tiles.filter((t) => {
    if (t.position === center.position) return false;
    const d = Math.hypot(t.properties.x - x, t.properties.y - y);
    return d > NEIGHBOR_DISTANCE * 0.8 && d < NEIGHBOR_DISTANCE * 1.15;
  });
}

export type HeroFxRun = {
  id: number;
  heroId: string;
  recipe: HeroFxRecipe;
  faction: string | null;
  color: string | null;
  /** Kafle wymienione przez bohatera (odsłaniane w `recipe.revealAt`). */
  replaced?: ReplacedTile[];
  /** Planety, do których bohater dołączył kartę (cel „planet”). */
  planets?: string[];
  /** Miejsca działania bohatera (fakty `area`). */
  areas?: HeroArea[];
};

type HeroFxStore = {
  run: HeroFxRun | null;
  /** Pozycja -> kafel sprzed wymiany: `MapTile` rysuje go, póki efekt go nie odsłoni. */
  covers: Record<string, string>;
  /**
   * Planety, których żeton zniszczenia czeka pod efektem (Stellar Converter): mapa go nie
   * rysuje, póki efekt nie odsłoni go w `recipe.revealAt`.
   */
  veiledPlanets: Record<string, true>;
  setVeiledPlanets: (planets: Record<string, true>) => void;
  unveilPlanet: (planet: string) => void;
  /** Kolejka momentów (scena bohatera itd.) niepusta - inne sceny (relikt) czekają na koniec. */
  stageBusy: boolean;
  setStageBusy: (busy: boolean) => void;
  play: (run: Omit<HeroFxRun, "id">) => void;
  stop: () => void;
  setCovers: (covers: Record<string, string>) => void;
  uncover: (position: string) => void;
};

/** Bieżący efekt na planszy (jeden naraz) — uruchamia `KeyMomentStage`, rysuje warstwa mapy. */
export const useHeroFx = create<HeroFxStore>((set) => ({
  run: null,
  covers: {},
  veiledPlanets: {},
  setVeiledPlanets: (veiledPlanets) => set({ veiledPlanets }),
  unveilPlanet: (planet) =>
    set((s) => {
      if (!(planet in s.veiledPlanets)) return s;
      const rest = { ...s.veiledPlanets };
      delete rest[planet];
      return { veiledPlanets: rest };
    }),
  stageBusy: false,
  setStageBusy: (stageBusy) => set((s) => (s.stageBusy === stageBusy ? s : { stageBusy })),
  play: (run) => set({ run: { ...run, id: Date.now() } }),
  stop: () => set({ run: null }),
  setCovers: (covers) => set({ covers }),
  uncover: (position) =>
    set((s) => {
      if (!(position in s.covers)) return s;
      const rest = { ...s.covers };
      delete rest[position];
      return { covers: rest };
    }),
}));

/** Zasłony kafli dla kolejki momentów: każdy czekający bohater z wymianą kafla. */
export function coversForQueue(queue: { kind: string; replaced?: ReplacedTile[] }[]) {
  const covers: Record<string, string> = {};
  for (const m of queue) for (const r of m.replaced ?? []) covers[r.position] ??= r.from;
  return covers;
}

/** Planety zniszczone w czekających momentach Stellar Converter (żeton czeka na wybuch). */
export function veiledPlanetsForQueue(queue: { kind: string; planet?: string }[]) {
  const veiled: Record<string, true> = {};
  for (const m of queue) if (m.kind === "converter" && m.planet) veiled[m.planet] = true;
  return veiled;
}
