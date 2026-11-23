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
  /** Tryb „gain” (Research Grant Reallocation): żetony do zdjęcia z puli za tę technologię. */
  tokenCost?: number;
  /** Brother Omar: zwrot 1 piechoty ignoruje wszystkie prerekwizyty tej technologii. */
  infantrySkip?: boolean;
  /** Riftmeld: przechwycone jednostki typu ulepszenia, których zwrot ignoruje prerekwizyty. */
  capturedSkips?: CapturedSkip[];
};

/** Riftmeld (RULES.md 62.17): skip `captured:<właściciel | token>` + chip jednostki. */
export type CapturedSkip = {
  value: string;
  unit: string;
  count: number;
  player: string;
  faction: string | null;
  color: string | null;
};
export const CAPTURED_SKIP_PREFIX = "captured:";

/** Brother Omar: skąd zwrócić piechotę (skip = `infantry:<pozycja>|<strefa>`). */
export type InfantrySkip = { value: string; label: string };
export const INFANTRY_SKIP_PREFIX = "infantry:";
/** Karta, która za wyczerpanie i OSOBNĄ zapłatę ignoruje wszystkie prerekwizyty (Inheritance Systems). */
export type PaidSkip = { card: string; name: string; cost: number };
export const PAID_SKIP_PREFIX = "paid:";

/** Skip `paid:<karta>|<planety>|<tg>` - zapłata osobno od kosztu badania. */
export function paidSkipValue(card: string, planets: string[], tradeGoods: number): string {
  return `${PAID_SKIP_PREFIX}${card}|${planets.join(",")}|${tradeGoods}`;
}

/**
 * Tryb „GAIN” okna: technologia przychodzi bez płatności i bez prerekwizytów (Research Grant
 * Reallocation). ``tokenPool`` - pula, z której zdejmuje się żetony (koszt na kaflu).
 */
export type GainMode = {
  mandatory: boolean;
  tokenPool: string | null;
  tokens: number;
  note: string;
};

export type ResearchOptions = {
  tree: TechRow[];
  ownedColors: Partial<Record<TechColor, number>>;
  /** Gotowe planety ze specjalnością → kolory. */
  specialties: Record<string, TechColor[]>;
  aida: boolean;
  /** Gotowe relikty ignorujące 1 prerekwizyt (Prophet's Tears); skip = `relic:<id>`. */
  relicSkips: string[];
  /** Brother Omar: miejsca z piechotą do zwrotu (ignoruje prerekwizyty technologii innego gracza). */
  infantrySkips: InfantrySkip[];
  /** Inheritance Systems: wyczerpanie + osobna zapłata ignoruje wszystkie prerekwizyty. */
  paidSkips: PaidSkip[];
  /** Gotowe planety → zasoby (płatność). */
  planets: Record<string, number>;
  tradeGoods: number;
  /** Wartość 1 TG w płatności (Mirror Computing: 2). */
  tradeGoodValue: number;
  cost: number;
  researched: string[];
  /** Przełom frakcji (Thunder's Edge) - synergia 2 kolorów, działa tylko odblokowany. */
  breakthrough: BreakthroughInfo | null;
  /** Zniżka kosztu (Doctor Sucaban), już odjęta od `cost`. */
  discount: number;
  /** Specialist Compounds: gotowe planety, które mogą zapłacić za badanie → ich kolory. */
  compoundPlanets: Record<string, TechColor[]>;
  /** Płatność wyłącznie w TG (Focused Research): bez planet, 1 TG = 1 do kosztu. */
  tradeGoodsOnly: boolean;
  /** Brilliant: secondary jak primary - druga technologia za `second.cost` (opcjonalna). */
  asPrimary: boolean;
  second: ResearchOptions | null;
  gain: GainMode | null;
};

export type BreakthroughInfo = {
  id: string;
  name: string;
  synergy: TechColor[];
  unlocked: boolean;
  exhausted: boolean;
  /** Synergia działa teraz (przełom odblokowany i ma parę kolorów). */
  active: boolean;
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
    relicSkips: Array.isArray(raw.relic_skips) ? (raw.relic_skips as string[]) : [],
    infantrySkips: Array.isArray(raw.infantry_skips)
      ? (raw.infantry_skips as InfantrySkip[])
      : [],
    paidSkips: Array.isArray(raw.paid_skips) ? (raw.paid_skips as PaidSkip[]) : [],
    planets: (raw.planets ?? {}) as Record<string, number>,
    tradeGoods: typeof raw.trade_goods === "number" ? raw.trade_goods : 0,
    // Karta „Spend N trade goods” liczy sztuki TG, nie ich wartość (Mirror Computing nie działa).
    tradeGoodValue:
      raw.trade_goods_only !== true && typeof raw.trade_good_value === "number"
        ? raw.trade_good_value
        : 1,
    tradeGoodsOnly: raw.trade_goods_only === true,
    cost: typeof raw.cost === "number" ? raw.cost : 0,
    researched: Array.isArray(raw.researched) ? (raw.researched as string[]) : [],
    breakthrough:
      raw.breakthrough && typeof raw.breakthrough === "object"
        ? (raw.breakthrough as BreakthroughInfo)
        : null,
    discount: typeof raw.discount === "number" ? raw.discount : 0,
    compoundPlanets: (raw.compound_planets ?? {}) as Record<string, TechColor[]>,
    asPrimary: raw.as_primary === true,
    gain:
      raw.gain && typeof raw.gain === "object" ? (raw.gain as GainMode) : null,
    second:
      raw.second && typeof raw.second === "object"
        ? toResearchOptions(raw.second as Record<string, unknown>)
        : null,
  };
}

/** Specialist Compounds: planety, które mogą zapłacić za TĘ technologię (kolor, bez ulepszeń). */
export function compoundChoices(
  row: TechRow | null,
  options: ResearchOptions,
  skips: string[],
): string[] {
  if (!row || row.unitUpgrade || row.color == null || options.cost <= 0) return [];
  return Object.entries(options.compoundPlanets)
    .filter(([id, colors]) => colors.includes(row.color as TechColor) && !skips.includes(id))
    .map(([id]) => id)
    .sort();
}

/**
 * Brilliant: opcje drugiego badania po pierwszym (lokalnie) - pierwsza technologia jako
 * posiadana, jej kolor liczy się do prerekwizytów. Backend i tak waliduje całość.
 */
export function afterFirstResearch(second: ResearchOptions, firstId: string): ResearchOptions {
  const first = second.tree.find((r) => r.id === firstId);
  const color = first?.color ?? null;
  const tree = second.tree.map((r) => {
    if (r.id === firstId) return { ...r, status: "owned" as TechStatus };
    if (!color || r.status === "owned" || r.status === "exhausted") return r;
    const need = r.missing[color] ?? 0;
    if (need <= 0) return r;
    const missing = { ...r.missing, [color]: need - 1 };
    if (missing[color] === 0) delete missing[color];
    const none = Object.values(missing).every((n) => (n ?? 0) <= 0);
    return { ...r, missing, status: none ? ("available" as TechStatus) : r.status };
  });
  const ownedColors = color
    ? { ...second.ownedColors, [color]: (second.ownedColors[color] ?? 0) + 1 }
    : second.ownedColors;
  return { ...second, tree, ownedColors };
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
  // Relikt „ignore 1 prerequisite" (Prophet's Tears): pokrywa jeden brakujący symbol.
  for (const relic of options.relicSkips) {
    const color = (Object.keys(left) as TechColor[]).find((c) => (left[c] ?? 0) > 0);
    if (!color) break;
    left[color] = (left[color] ?? 0) - 1;
    skips.push(`relic:${relic}`);
  }
  // Brother Omar: gdy zwykłe skipy nie wystarczą, sama piechota ignoruje wszystko (bez planet).
  const rest = Object.values(left).reduce((s, n) => s + Math.max(0, n ?? 0), 0);
  if (rest > 0 && row.infantrySkip && options.infantrySkips.length > 0) {
    return { skips: [options.infantrySkips[0].value], left: {} };
  }
  // Riftmeld: tak samo - zwrot przechwyconej jednostki ignoruje wszystkie prerekwizyty.
  if (rest > 0 && row.capturedSkips && row.capturedSkips.length > 0) {
    return { skips: [row.capturedSkips[0].value], left: {} };
  }
  return { skips, left };
}

/** Ile symboli wciąż brakuje po zastosowaniu podanych skipów. */
export function remainingAfter(
  row: TechRow,
  skips: string[],
  options: ResearchOptions,
): Partial<Record<TechColor, number>> {
  if (
    skips.some(
      (s) =>
        s.startsWith(INFANTRY_SKIP_PREFIX) ||
        s.startsWith(PAID_SKIP_PREFIX) ||
        s.startsWith(CAPTURED_SKIP_PREFIX),
    )
  ) {
    return {};
  }
  const left: Partial<Record<TechColor, number>> = { ...row.missing };
  for (const skip of skips) {
    if (skip === AIDA_SKIP || skip.startsWith("relic:")) {
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
  tgValue = 1,
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
  const tg = Math.min(tradeGoods, Math.ceil(Math.max(0, cost - total) / tgValue));
  return { planets: chosen.map(([id]) => id), tradeGoods: tg };
}
