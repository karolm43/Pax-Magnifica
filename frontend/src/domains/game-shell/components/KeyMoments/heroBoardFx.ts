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
  | "planet"; // system planety, do której bohater dołączył kartę (Geoform -> Elysium)

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
  | "awaken"; // Titans: przebudzenie Elysium

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
