/**
 * Efekty bohaterów NA PLANSZY (RULES.md 64.4) — po scenie bohatera mapa „reaguje” na jego
 * zdolność. Dane (który bohater -> jaki przepis) + czyste wyliczenie celów z kafelków mapy.
 * Rysuje `HeroBoardFxLayer` (warstwa w treści mapy, więc idzie za przesuwaniem i zoomem).
 * Nowy bohater w silniku => dopisz przepis tutaj (inaczej zostaje sama scena).
 */
import { create } from "zustand";
import type { Tile } from "@/entities/game/types";
import type { SoundName } from "@/domains/battle/battleSound";
import type { ReplacedTile } from "./keyMoments";

/** Gdzie na planszy dzieje się efekt. */
export type FxTarget =
  | "ground" // systemy z siłami naziemnymi bohatera
  | "defense" // systemy z PDS albo mechami bohatera (obrona planet)
  | "ships" // systemy ze statkami bohatera
  | "units" // systemy z dowolnymi jednostkami bohatera
  | "active" // aktywny system (produkcja / walka / inwazja), inaczej „units”
  | "mecatol" // Mecatol Rex
  | "nova"; // kafel supernowej Muaat (Nova Seed) — po wymianie kafla

/** Wygląd efektu w systemie docelowym. */
export type FxMark = "bloom" | "beam" | "coins" | "ripple" | "slash" | "seal" | "pulse" | "aegis" | "nova";

export type HeroFxRecipe = {
  /** Przyciemnienie całej planszy (0–1). */
  dim?: number;
  /** Fala przez całą planszę (lewa -> prawa). */
  sweep?: "scan" | "dawn";
  /** Cienie statków przepływające nad planszą (typy jednostek AsyncTI4). */
  shadows?: string[];
  target: FxTarget;
  mark: FxMark;
  /** Kolor efektu (rgb), domyślnie kolor gracza. */
  tone?: string;
  /** Czas efektu (ms). */
  ms: number;
  /** Dźwięki efektu (ms od startu, próbki walki — `battleSound`). */
  sounds?: { at: number; name: SoundName; gain?: number }[];
  /** Chwila (ms), w której wymieniony kafel odsłania nowy (pod błyskiem); domyślnie od razu. */
  revealAt?: number;
};

/** Bohaterowie zaimplementowani w silniku (`core/hooks/factions/*`). */
export const HERO_BOARD_FX: Record<string, HeroFxRecipe> = {
  // Void Transference: brak limitu floty — plansza ciemnieje pod cieniami okrętów.
  letnevhero: { dim: 0.6, shadows: ["dn", "fs", "dn", "ca", "dn"], target: "ships", mark: "pulse", tone: "255 70 60", ms: 5200 },
  // Overgrowth: produkcja wszędzie, gdzie są siły naziemne — zieleń wyrasta z planet.
  arborechero: { dim: 0.25, target: "ground", mark: "bloom", tone: "120 230 110", ms: 4400 },
  // Twilight Directive: żetony dowodzenia wracają — złota fala zmierzchu i słupy światła.
  solhero: { dim: 0.3, sweep: "dawn", target: "units", mark: "beam", tone: "255 205 90", ms: 4400 },
  // Brilliance of the Hylar: wymiana technologii — skan danych przez całą planszę.
  jolnarhero: { dim: 0.3, sweep: "scan", target: "units", mark: "pulse", tone: "90 180 255", ms: 4200 },
  // Sanction of the Quieron: darmowa produkcja — deszcz trade goods nad systemem.
  hacanhero: { dim: 0.3, target: "active", mark: "coins", tone: "255 200 70", ms: 4000 },
  // Insurrection: zniszczone statki wroga wracają jako Mentak — fale w systemie walki.
  mentakhero: { dim: 0.35, target: "active", mark: "ripple", tone: "255 120 60", ms: 4000 },
  // Brood Swarm: prosto do lądowania — szpony uderzają w system inwazji.
  sardakkhero: { dim: 0.35, target: "active", mark: "slash", tone: "255 60 50", ms: 3800 },
  // Sins of the Father: dowolna karta strategii — pieczęć imperium nad Mecatol Rex.
  winnuhero: { dim: 0.35, target: "mecatol", mark: "seal", tone: "255 210 90", ms: 4400 },
  // Planetary Defense Nexus - Aegis: PDS i mechy na planetach — kopuły tarcz wznoszą się nad nimi.
  "xxchahero-te": { dim: 0.3, target: "defense", mark: "aegis", tone: "110 230 190", ms: 4400 },
  // Helix Protocol: skrzydła Argent przeskakują do systemów z żetonami — cienie niszczycieli i słupy światła.
  argenthero: { dim: 0.4, shadows: ["dd", "dd", "fs", "dd"], target: "ships", mark: "beam", tone: "255 150 60", ms: 4400 },
  // Quantum Dissemination: piechota z rezerwy ląduje na planetach — impulsy nad systemami walk.
  yinhero: { dim: 0.4, target: "ground", mark: "pulse", tone: "235 235 245", ms: 4200 },
  // Dark Space Navigation: flagowiec i pancerniki wychodzą z mroku w jednym systemie — cienie i słupy.
  l1z1xhero: { dim: 0.5, shadows: ["dn", "fs", "dn"], target: "ships", mark: "beam", tone: "210 60 60", ms: 4400 },
  // Nova Seed: system staje się supernową — błysk, fala uderzeniowa i wyrzuty plazmy z nowego kafla.
  // Stary kafel zostaje do błysku (revealAt), nowa supernowa wyłania się z poświaty.
  muaathero: {
    dim: 0.55,
    target: "nova",
    mark: "nova",
    tone: "255 130 50",
    ms: 5200,
    revealAt: 1650,
    sounds: [
      { at: 0, name: "warSunEnter", gain: 0.55 },
      { at: 1550, name: "explosionHeavy", gain: 0.9 },
      { at: 1700, name: "explosion", gain: 0.5 },
    ],
  },
};

const GROUND = new Set(["gf", "mf"]);
const DEFENSE = new Set(["pd", "mf"]);
const MECATOL_SYSTEM_IDS = new Set(["18", "112"]);
/** Kafel „Nova Seed” (supernowa Muaat, `assets/systems/81.json`) — jeden w grze. */
const NOVA_SEED_SYSTEM_ID = "81";

/** Jednostki gracza w kafelku (klucz `unitsByFaction` = frakcja; zapasowo kolor). */
function unitsOf(tile: Tile, keys: string[]) {
  const pick = (m: Record<string, { entityId: string; count: number }[]>) =>
    keys.flatMap((k) => m[k] ?? []);
  const space = pick(tile.unitsByFaction);
  const planets = Object.values(tile.planets).flatMap((p) => pick(p.unitsByFaction ?? {}));
  return { space, planets };
}

/** Pozycje systemów, w których dzieje się efekt. */
export function fxTargets(
  recipe: HeroFxRecipe,
  tiles: Tile[],
  owner: { faction: string | null; color: string | null },
  activeSystem: string | null,
): string[] {
  const keys = [owner.faction, owner.color].filter((k): k is string => !!k);
  const pick = (test: (t: Tile) => boolean) => tiles.filter(test).map((t) => t.position);
  switch (recipe.target) {
    case "mecatol":
      return pick((t) => MECATOL_SYSTEM_IDS.has(t.systemId)).slice(0, 1);
    case "nova":
      return pick((t) => t.systemId === NOVA_SEED_SYSTEM_ID).slice(0, 1);
    case "active":
      if (activeSystem && tiles.some((t) => t.position === activeSystem)) return [activeSystem];
      return fxTargets({ ...recipe, target: "units" }, tiles, owner, null);
    case "ground":
      return pick((t) =>
        unitsOf(t, keys).planets.some((u) => GROUND.has(u.entityId) && u.count > 0),
      );
    case "defense":
      return pick((t) =>
        unitsOf(t, keys).planets.some((u) => DEFENSE.has(u.entityId) && u.count > 0),
      );
    case "ships":
      return pick((t) => unitsOf(t, keys).space.some((u) => !GROUND.has(u.entityId) && u.count > 0));
    case "units":
      return pick((t) => {
        const u = unitsOf(t, keys);
        return [...u.space, ...u.planets].some((x) => x.count > 0);
      });
  }
}

export type HeroFxRun = {
  id: number;
  heroId: string;
  recipe: HeroFxRecipe;
  faction: string | null;
  color: string | null;
  /** Kafle wymienione przez bohatera (odsłaniane w `recipe.revealAt`). */
  replaced?: ReplacedTile[];
};

type HeroFxStore = {
  run: HeroFxRun | null;
  /** Pozycja -> kafel sprzed wymiany: `MapTile` rysuje go, póki efekt go nie odsłoni. */
  covers: Record<string, string>;
  play: (run: Omit<HeroFxRun, "id">) => void;
  stop: () => void;
  setCovers: (covers: Record<string, string>) => void;
  uncover: (position: string) => void;
};

/** Bieżący efekt na planszy (jeden naraz) — uruchamia `KeyMomentStage`, rysuje warstwa mapy. */
export const useHeroFx = create<HeroFxStore>((set) => ({
  run: null,
  covers: {},
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
