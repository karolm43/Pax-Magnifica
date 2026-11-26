import type { PlayerData } from "@/entities/data/types";
import type { Tile } from "@/entities/game/types";
import { empireStats, type EmpireStats } from "./empireStats";

/*
 * Empire vs. the table: for each measure, the shown player's value, their place among all seated
 * players, who leads and what is in play in total. Pure: reads only web-data (player data and the
 * engine's board), the same numbers the rest of the tab shows.
 */

export type CompareRow = {
  id: string;
  label: string;
  /** Short explanation (hover). */
  hint: string;
  value: number;
  /** 1 = best; players with the same value share a place. */
  rank: number;
  players: number;
  /** Leading player(s) and their value. */
  leaders: PlayerData[];
  best: number;
  /** Sum over all players, or what exists in the game (planets on the map); null = not summable. */
  total: number | null;
  totalLabel: string;
};

type Measure = {
  id: string;
  label: string;
  hint: string;
  get: (p: PlayerData, e: EmpireStats) => number;
  /** A per-player best, not an amount: no table total. */
  noTotal?: boolean;
};

const MEASURES: Measure[] = [
  { id: "vp", label: "Victory points", hint: "Victory points scored", get: (p) => p.totalVps ?? 0 },
  { id: "planets", label: "Planets", hint: "Planets controlled", get: (_, e) => e.planets.total },
  { id: "resources", label: "Resources", hint: "Total resource value of controlled planets", get: (p) => p.totResources ?? 0 },
  { id: "influence", label: "Influence", hint: "Total influence value of controlled planets", get: (p) => p.totInfluence ?? 0 },
  { id: "techs", label: "Technologies", hint: "Technologies researched", get: (p) => p.techs?.length ?? 0 },
  { id: "systems", label: "Systems", hint: "Systems with your units or planets", get: (_, e) => e.systems.present },
  { id: "ships", label: "Ships", hint: "Non-fighter ships on the board", get: (_, e) => e.forces.ships },
  { id: "fighters", label: "Fighters", hint: "Fighters on the board", get: (_, e) => e.forces.fighters },
  { id: "ground", label: "Ground forces", hint: "Infantry and mechs on the board", get: (_, e) => e.forces.ground },
  { id: "structures", label: "Structures", hint: "Space docks and PDS on the board", get: (_, e) => e.forces.docks + e.forces.pds },
  { id: "production", label: "Best PRODUCTION", hint: "Highest PRODUCTION in one system", get: (_, e) => e.maxProduction, noTotal: true },
  { id: "tg", label: "Trade goods", hint: "Trade goods in hand", get: (p) => p.tg ?? 0 },
  { id: "ac", label: "Action cards", hint: "Action cards in hand", get: (p) => p.acCount ?? 0 },
  {
    id: "tokens",
    label: "Command tokens",
    hint: "Tokens in tactic, fleet and strategy pools",
    get: (p) => (p.tacticalCC ?? 0) + (p.fleetCC ?? 0) + (p.strategicCC ?? 0),
  },
];

/** Planets on the map (controlled or not). */
function planetsOnMap(tiles: Record<string, Tile> | undefined): number {
  return Object.values(tiles ?? {}).reduce((sum, t) => sum + Object.keys(t.planets ?? {}).length, 0);
}

export function compareEmpires(
  shown: PlayerData,
  players: PlayerData[],
  tiles: Record<string, Tile> | undefined,
): CompareRow[] {
  const seated = players.some((p) => p.color === shown.color) ? players : [...players, shown];
  const stats = new Map(seated.map((p) => [p.color, empireStats(p, tiles)]));
  const mapPlanets = planetsOnMap(tiles);

  return MEASURES.map(({ id, label, hint, get, noTotal }) => {
    const values = seated.map((p) => ({ p, v: get(p, stats.get(p.color)!) }));
    const value = values.find((x) => x.p.color === shown.color)!.v;
    const best = Math.max(...values.map((x) => x.v));
    const sum = values.reduce((s, x) => s + x.v, 0);
    const onMap = id === "planets" && mapPlanets > 0;
    return {
      id,
      label,
      hint,
      value,
      rank: 1 + values.filter((x) => x.v > value).length,
      players: seated.length,
      leaders: best > 0 ? values.filter((x) => x.v === best).map((x) => x.p) : [],
      best,
      total: noTotal ? null : onMap ? mapPlanets : sum,
      totalLabel: onMap ? "on the map" : "at the table",
    };
  });
}
