import type { PlayerData } from "@/entities/data/types";
import type { Tile } from "@/entities/game/types";
import { getPlanetData } from "@/entities/lookup/planets";
import { lookupUnit } from "@/entities/lookup/units";
import { mergePlanetTraits, type PlanetTrait } from "@/entities/game/planetTraits";
import type { TechType } from "@/shared/ui/TechSkipIcon";

/*
 * Statystyki imperium do PANELU DOWÓDCY (zakładka „Player”): czysta funkcja z web-data. Nic nie
 * liczy reguł od nowa - czyta to, co policzył silnik (kontrola planet, jednostki w systemach,
 * PRODUCTION per system, ready/exhausted), a z danych AsyncTI4 bierze tylko cechy planet i koszty.
 *
 * Kalkulator „co zbuduję” trzyma się R_producing_units: koszt z dwiema ikonami (fighter, infantry)
 * daje 2 jednostki, a KAŻDA liczy się do limitu PRODUCTION; te dwie jednostki mogą też być
 * żetonami z puli, więc nie ogranicza ich liczba plastików w posiłkach.
 */

/** Typy jednostek w kalkulatorze budowy, w kolejności jak w strefie gracza. */
const BUILD_ORDER = ["ws", "fs", "dn", "cv", "ca", "dd", "ff", "mf", "gf"];
/** Jednostki „dwie za koszt”, dobierane też jako żetony (R_producing_units). */
const TOKEN_UNITS = new Set(["ff", "gf"]);
const SHIP_IDS = new Set(["ws", "fs", "dn", "cv", "ca", "dd", "ff"]);
const TECH_COLORS: TechType[] = ["biotic", "propulsion", "cybernetic", "warfare"];

export type BuildOption = {
  asyncId: string;
  name: string;
  cost: number;
  /** Ile maksymalnie: min(zasoby, PRODUCTION największego systemu, posiłki, miejsce w puli floty). */
  max: number;
  /** Co ogranicza ``max`` (do podpowiedzi). */
  limitedBy: "resources" | "production" | "reinforcements" | "fleetPool";
  /** Posiłki; null = bez limitu (żetony fighter/infantry). */
  reinforcements: number | null;
};

export type EmpireStats = {
  planets: { total: number; ready: number; legendary: number };
  traits: Record<PlanetTrait, number>;
  /** Specjalizacje technologiczne na GOTOWYCH planetach (do badania technologii). */
  skips: Record<TechType, number>;
  systems: { present: number; controlled: number };
  forces: { ships: number; fighters: number; ground: number; docks: number; pds: number };
  /** Największa flota (nie-myśliwce w jednym systemie) vs pula floty. */
  largestFleet: number;
  fleetPool: number;
  /** Najwyższa wartość PRODUCTION w jednym systemie (silnik). */
  maxProduction: number;
  /** Systems where the player has PRODUCTION (engine value), highest first. */
  productionSystems: { position: string; label: string; value: number }[];
  /** Zasoby do wydania: gotowe planety + trade goods. */
  budget: number;
  /** Wpływy gotowych planet (silnik: ``influence``) - bez trade goods. */
  readyInfluence: number;
  /**
   * Ile jeszcze nie-myśliwców zmieści pula floty w najlepszym systemie z PRODUCTION
   * (pula − statki już tam stojące); null = brak systemu z PRODUCTION.
   */
  fleetRoom: number | null;
  build: BuildOption[];
  /** Typy jednostek bez plastików w posiłkach (poza żetonami fighter/infantry). */
  depleted: string[];
};

function deployed(player: PlayerData, asyncId: string): number {
  return player.unitCounts?.[asyncId]?.deployedCount ?? 0;
}

function reinforcementsLeft(player: PlayerData, asyncId: string): number | null {
  if (TOKEN_UNITS.has(asyncId)) return null;
  const entry = player.unitCounts?.[asyncId];
  if (!entry || entry.unitCap <= 0) return null;
  return Math.max(0, entry.unitCap - entry.deployedCount);
}

export function empireStats(
  player: PlayerData,
  tiles: Record<string, Tile> | undefined,
): EmpireStats {
  const exhausted = new Set(player.exhaustedPlanets);
  const traits: Record<PlanetTrait, number> = { cultural: 0, hazardous: 0, industrial: 0 };
  const skips: Record<TechType, number> = { biotic: 0, propulsion: 0, cybernetic: 0, warfare: 0 };
  let legendary = 0;
  for (const id of player.planets) {
    const planet = getPlanetData(id);
    if (!planet) continue;
    for (const trait of mergePlanetTraits(planet.planetTypes, [planet.planetType ?? ""])) {
      traits[trait] += 1;
    }
    if (planet.legendaryAbilityName) legendary += 1;
    if (exhausted.has(id)) continue;
    for (const spec of planet.techSpecialties ?? []) {
      const color = spec.toLowerCase() as TechType;
      if (TECH_COLORS.includes(color)) skips[color] += 1;
    }
  }

  const fleetPool = player.fleetCC + (player.mahactEdict?.length ?? 0);
  let present = 0;
  let controlled = 0;
  let largestFleet = 0;
  let maxProduction = 0;
  let fleetRoom: number | null = null;
  const productionSystems: EmpireStats["productionSystems"] = [];
  for (const tile of Object.values(tiles ?? {})) {
    const own = tile.unitsByFaction?.[player.faction] ?? [];
    const planets = Object.values(tile.planets ?? {});
    const mine =
      own.length > 0 ||
      planets.some(
        (p) => p.controlledBy === player.faction || (p.unitsByFaction?.[player.faction]?.length ?? 0) > 0,
      );
    if (!mine) continue;
    present += 1;
    const others =
      Object.keys(tile.unitsByFaction ?? {}).some((f) => f !== player.faction && f !== "neutral") ||
      planets.some((p) => p.controlledBy != null && p.controlledBy !== player.faction);
    if (!others) controlled += 1;
    const fleet = own
      .filter((e) => e.entityType === "unit" && SHIP_IDS.has(e.entityId) && e.entityId !== "ff")
      .reduce((sum, e) => sum + e.count, 0);
    largestFleet = Math.max(largestFleet, fleet);
    const production = tile.productionByColor?.[player.color] ?? 0;
    maxProduction = Math.max(maxProduction, production);
    if (production > 0) {
      fleetRoom = Math.max(fleetRoom ?? 0, Math.max(0, fleetPool - fleet));
      const names = Object.keys(tile.planets ?? {})
        .map((id) => getPlanetData(id)?.name)
        .filter((n): n is string => Boolean(n));
      productionSystems.push({
        position: tile.position,
        label: names.length > 0 ? names.join(" / ") : `System ${tile.position}`,
        value: production,
      });
    }
  }

  const budget = Math.max(0, Math.floor(player.resources ?? 0)) + (player.tg ?? 0);
  const build: BuildOption[] = [];
  const depleted: string[] = [];
  for (const asyncId of BUILD_ORDER) {
    const unit = lookupUnit(asyncId, player.faction, player);
    if (!unit || unit.id.toLowerCase() === "nowarsun" || !unit.cost || unit.cost <= 0) continue;
    const reinforcements = reinforcementsLeft(player, asyncId);
    if (reinforcements === 0) depleted.push(unit.name);
    const byCost = Math.floor(budget / unit.cost);
    const caps: [BuildOption["limitedBy"], number][] = [
      ["resources", byCost],
      ["production", maxProduction],
    ];
    if (reinforcements !== null) caps.push(["reinforcements", reinforcements]);
    // R_fleet_pool: non-fighter ships count against the fleet pool in the system they are built in.
    if (fleetRoom !== null && SHIP_IDS.has(asyncId) && asyncId !== "ff") caps.push(["fleetPool", fleetRoom]);
    const [limitedBy, max] = caps.reduce((a, b) => (b[1] < a[1] ? b : a));
    build.push({ asyncId, name: unit.name, cost: unit.cost, max, limitedBy, reinforcements });
  }

  return {
    planets: {
      total: player.planets.length,
      ready: player.planets.filter((p) => !exhausted.has(p)).length,
      legendary,
    },
    traits,
    skips,
    systems: { present, controlled },
    forces: {
      ships: ["ws", "fs", "dn", "cv", "ca", "dd"].reduce((s, id) => s + deployed(player, id), 0),
      fighters: deployed(player, "ff"),
      ground: deployed(player, "gf") + deployed(player, "mf"),
      docks: deployed(player, "sd"),
      pds: deployed(player, "pd"),
    },
    largestFleet,
    fleetPool,
    maxProduction,
    productionSystems: productionSystems.sort((a, b) => b.value - a.value),
    budget,
    readyInfluence: Math.max(0, Math.floor(player.influence ?? 0)),
    fleetRoom,
    build,
    depleted,
  };
}
