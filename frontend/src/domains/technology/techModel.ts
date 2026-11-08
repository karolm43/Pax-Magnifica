/*
 * Model danych okna badania technologii (RULES.md 49). Dane drzewa liczy backend
 * (`core/technology.tree_view` przez `/strategy/options`), tu tylko typy i czyste
 * pomocnicze funkcje UI (układ drzewa, automatyczny dobór skipów, suma płatności).
 */

export type TechColor = "PROPULSION" | "BIOTIC" | "CYBERNETIC" | "WARFARE";

export type TechStatus = "owned" | "exhausted" | "available" | "skippable" | "locked";

export type TechRow = {
  id: string;
  name: string;
  color: TechColor | null;
  unitUpgrade: boolean;
  faction: string | null;
  baseUpgrade: string | null;
  prerequisites: TechColor[];
  missing: Partial<Record<TechColor, number>>;
  status: TechStatus;
};

export type ResearchOptions = {
  tree: TechRow[];
  ownedColors: Partial<Record<TechColor, number>>;
  /** Gotowe planety ze specjalnością → kolory. */
  specialties: Record<string, TechColor[]>;
  aida: boolean;
  /** Gotowe planety → zasoby (płatność). */
  planets: Record<string, number>;
  tradeGoods: number;
  cost: number;
  researched: string[];
};

/** Kolumny drzewa: kolejność jak na kartach (niebieski, zielony, żółty, czerwony). */
export const COLUMNS: { color: TechColor; label: string; icon: string; hue: string }[] = [
  { color: "PROPULSION", label: "Propulsion", icon: "/blue.png", hue: "56 132 255" },
  { color: "BIOTIC", label: "Biotic", icon: "/green.png", hue: "52 199 89" },
  { color: "CYBERNETIC", label: "Cybernetic", icon: "/yellow.png", hue: "245 196 40" },
  { color: "WARFARE", label: "Warfare", icon: "/red.png", hue: "232 64 64" },
];

export const COLOR_ICON: Record<TechColor, string> = {
  PROPULSION: "/blue.png",
  BIOTIC: "/green.png",
  CYBERNETIC: "/yellow.png",
  WARFARE: "/red.png",
};

export const COLOR_HUE: Record<TechColor, string> = Object.fromEntries(
  COLUMNS.map((c) => [c.color, c.hue]),
) as Record<TechColor, string>;

/** Odczyt opcji z luźnego słownika backendu (snake_case → camelCase). */
export function toResearchOptions(raw: Record<string, unknown>): ResearchOptions {
  return {
    tree: Array.isArray(raw.tree) ? (raw.tree as TechRow[]) : [],
    ownedColors: (raw.owned_colors ?? {}) as ResearchOptions["ownedColors"],
    specialties: (raw.specialties ?? {}) as ResearchOptions["specialties"],
    aida: raw.aida === true,
    planets: (raw.planets ?? {}) as Record<string, number>,
    tradeGoods: typeof raw.trade_goods === "number" ? raw.trade_goods : 0,
    cost: typeof raw.cost === "number" ? raw.cost : 0,
    researched: Array.isArray(raw.researched) ? (raw.researched as string[]) : [],
  };
}

/** Liczba symboli prerekwizytów = „poziom" w kolumnie (0..3). */
export function tier(row: TechRow): number {
  return row.prerequisites.length;
}

/** Siatka drzewa: kolumna koloru → poziom → technologie (frakcyjne na końcu poziomu). */
export function layoutColumns(tree: TechRow[]): Record<TechColor, TechRow[][]> {
  const grid = Object.fromEntries(
    COLUMNS.map((c) => [c.color, [[], [], [], []] as TechRow[][]]),
  ) as Record<TechColor, TechRow[][]>;
  for (const row of tree) {
    if (row.unitUpgrade || row.color == null) continue;
    const level = Math.min(3, tier(row));
    grid[row.color][level].push(row);
  }
  for (const column of Object.values(grid)) {
    for (const cell of column) {
      cell.sort((a, b) => Number(!!a.faction) - Number(!!b.faction) || a.name.localeCompare(b.name));
    }
  }
  return grid;
}

/** Ulepszenia jednostek posortowane po liczbie prerekwizytów (jak rosnąca siła). */
export function unitUpgrades(tree: TechRow[]): TechRow[] {
  return tree
    .filter((r) => r.unitUpgrade)
    .sort((a, b) => tier(a) - tier(b) || a.name.localeCompare(b.name));
}

/** Pozostałe technologie bez koloru (np. frakcyjne specjalne). */
export function otherTechs(tree: TechRow[]): TechRow[] {
  return tree.filter((r) => !r.unitUpgrade && r.color == null);
}

export const AIDA_SKIP = "aida";

/**
 * Automatyczny dobór skipów: dla każdego brakującego symbolu najtańsza (najmniej zasobów)
 * gotowa planeta ze specjalnością tego koloru; brak planety → AIDA (tylko ulepszenia).
 * Zwraca listę skipów i resztę brakujących symboli (pusta = da się zbadać).
 */
export function autoSkips(
  row: TechRow,
  options: ResearchOptions,
): { skips: string[]; left: Partial<Record<TechColor, number>> } {
  const left: Partial<Record<TechColor, number>> = { ...row.missing };
  const skips: string[] = [];
  const planets = Object.entries(options.specialties).sort(
    ([a], [b]) => (options.planets[a] ?? 0) - (options.planets[b] ?? 0) || a.localeCompare(b),
  );
  for (const [planet, colors] of planets) {
    const color = colors.find((c) => (left[c] ?? 0) > 0);
    if (!color) continue;
    left[color] = (left[color] ?? 0) - 1;
    skips.push(planet);
  }
  const remaining = Object.values(left).reduce((s, n) => s + (n ?? 0), 0);
  if (remaining > 0 && row.unitUpgrade && options.aida) {
    const color = (Object.keys(left) as TechColor[]).find((c) => (left[c] ?? 0) > 0);
    if (color) {
      left[color] = (left[color] ?? 0) - 1;
      skips.push(AIDA_SKIP);
    }
  }
  return { skips, left };
}

/** Ile symboli wciąż brakuje po zastosowaniu podanych skipów. */
export function remainingAfter(
  row: TechRow,
  skips: string[],
  options: ResearchOptions,
): Partial<Record<TechColor, number>> {
  const left: Partial<Record<TechColor, number>> = { ...row.missing };
  for (const skip of skips) {
    if (skip === AIDA_SKIP) {
      const color = (Object.keys(left) as TechColor[]).find((c) => (left[c] ?? 0) > 0);
      if (color) left[color] = (left[color] ?? 0) - 1;
      continue;
    }
    const color = (options.specialties[skip] ?? []).find((c) => (left[c] ?? 0) > 0);
    if (color) left[color] = (left[color] ?? 0) - 1;
  }
  return left;
}

export function totalMissing(left: Partial<Record<TechColor, number>>): number {
  return Object.values(left).reduce((s, n) => s + Math.max(0, n ?? 0), 0);
}

/** Najtańsza płatność bez zbędnych planet: od największych, potem zdejmij nadmiarowe. */
export function autoPay(
  planets: Record<string, number>,
  exclude: string[],
  tradeGoods: number,
  cost: number,
): { planets: string[]; tradeGoods: number } {
  if (cost <= 0) return { planets: [], tradeGoods: 0 };
  const ranked = Object.entries(planets)
    .filter(([id, v]) => !exclude.includes(id) && v > 0)
    .sort(([a, x], [b, y]) => y - x || a.localeCompare(b));
  const chosen: [string, number][] = [];
  let total = 0;
  for (const entry of ranked) {
    if (total >= cost) break;
    chosen.push(entry);
    total += entry[1];
  }
  for (const entry of [...chosen].sort((a, b) => a[1] - b[1])) {
    if (total - entry[1] >= cost) {
      chosen.splice(chosen.indexOf(entry), 1);
      total -= entry[1];
    }
  }
  const tg = Math.min(tradeGoods, Math.max(0, cost - total));
  return { planets: chosen.map(([id]) => id), tradeGoods: tg };
}
