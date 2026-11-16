/**
 * Efekty bohaterów NA PLANSZY (RULES.md 64.4) — po scenie bohatera mapa „reaguje” na jego
 * zdolność. Dane (który bohater -> jaki przepis) + czyste wyliczenie celów z kafelków mapy.
 * Rysuje `HeroBoardFxLayer` (warstwa w treści mapy, więc idzie za przesuwaniem i zoomem).
 * Nowy bohater w silniku => dopisz przepis tutaj (inaczej zostaje sama scena).
 */
import { create } from "zustand";
import type { Tile } from "@/entities/game/types";

/** Gdzie na planszy dzieje się efekt. */
export type FxTarget =
  | "ground" // systemy z siłami naziemnymi bohatera
  | "defense" // systemy z PDS albo mechami bohatera (obrona planet)
  | "ships" // systemy ze statkami bohatera
  | "units" // systemy z dowolnymi jednostkami bohatera
  | "active" // aktywny system (produkcja / walka / inwazja), inaczej „units”
  | "mecatol"; // Mecatol Rex

/** Wygląd efektu w systemie docelowym. */
export type FxMark = "bloom" | "beam" | "coins" | "ripple" | "slash" | "seal" | "pulse" | "aegis";

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
  // Quantum Dissemination: piechota z rezerwy ląduje na planetach — impulsy nad systemami walk.
  yinhero: { dim: 0.4, target: "ground", mark: "pulse", tone: "235 235 245", ms: 4200 },
};

const GROUND = new Set(["gf", "mf"]);
const DEFENSE = new Set(["pd", "mf"]);
const MECATOL_SYSTEM_IDS = new Set(["18", "112"]);

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
};

type HeroFxStore = {
  run: HeroFxRun | null;
  play: (run: Omit<HeroFxRun, "id">) => void;
  stop: () => void;
};

/** Bieżący efekt na planszy (jeden naraz) — uruchamia `KeyMomentStage`, rysuje warstwa mapy. */
export const useHeroFx = create<HeroFxStore>((set) => ({
  run: null,
  play: (run) => set({ run: { ...run, id: Date.now() } }),
  stop: () => set({ run: null }),
}));
