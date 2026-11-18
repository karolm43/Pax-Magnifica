/*
 * Oficjalne, aktywne źródła kart — zgodne z `assets/enabled_sources.json`
 * backendu. Wygenerowane dane frontendu zawierają TĘ SAMĄ kartę z wielu źródeł
 * homebrew (absol, twilights_fall, …) pod różnymi aliasami; bez tego filtra listy
 * (pula kart, edytor gracza) dublowałyby pozycje. Trzymamy oficjalny zestaw:
 * base + pok + codex1–4 + thunders_edge.
 */
import {
  ACTIVE_DECK_IDS,
  VARIANT_MODULES,
  type ActiveDeckKind,
  type VariantModuleInfo,
} from "./activeDecks";

export const OFFICIAL_SOURCES: ReadonlySet<string> = new Set([
  "base",
  "pok",
  "codex1",
  "codex2",
  "codex3",
  "codex4",
  "thunders_edge",
]);

/** Czy karta pochodzi z aktywnego, oficjalnego źródła (patrz `OFFICIAL_SOURCES`). */
export function isOfficialSource(source: string): boolean {
  return OFFICIAL_SOURCES.has(source);
}

const activeDeckSets: Record<ActiveDeckKind, ReadonlySet<string>> = {
  agenda: new Set(ACTIVE_DECK_IDS.agenda),
  actionCard: new Set(ACTIVE_DECK_IDS.actionCard),
  relic: new Set(ACTIVE_DECK_IDS.relic),
  secretObjective: new Set(ACTIVE_DECK_IDS.secretObjective),
  stage1Objective: new Set(ACTIVE_DECK_IDS.stage1Objective),
  stage2Objective: new Set(ACTIVE_DECK_IDS.stage2Objective),
};

/**
 * Czy karta należy do AKTYWNEJ talii (tej, z której losuje silnik). Samo źródło nie
 * wystarcza: rozszerzenia usuwają stare karty (np. 13 agend w PoK), które nadal leżą w
 * danych base. Lista pochodzi z `scripts/gen_active_decks.py`.
 */
export function isInActiveDeck(kind: ActiveDeckKind, alias: string): boolean {
  return activeDeckSets[kind].has(alias);
}

// Moduły wariantów gry (fanowskie talie, erraty, własne komponenty) - wygenerowane z
// `assets/config/variants.json` (backend: `src/core/variants.py`, instrukcja: docs/WARIANTY.md).
// Gra niesie wybrane moduły w `cardPool.variants`; starsze gry tylko `cardPool.agendaVariant`.
const moduleById = new Map(VARIANT_MODULES.map((m) => [m.id, m]));
const moduleDeckSets = new Map(
  VARIANT_MODULES.map((m) => [
    m.id,
    Object.fromEntries(
      Object.entries(m.decks).map(([kind, ids]) => [kind, new Set(ids)]),
    ) as Partial<Record<ActiveDeckKind, ReadonlySet<string>>>,
  ]),
);

/** Moduły wariantów dostępne w Ustawieniach (kolejność z manifestu). */
export function variantModules(): readonly VariantModuleInfo[] {
  return VARIANT_MODULES;
}

/** Moduły włączone domyślnie w nowych grach (`"default": true` w manifeście). */
export function defaultVariantIds(): string[] {
  return VARIANT_MODULES.filter((m) => m.default).map((m) => m.id);
}

/**
 * Włącza/wyłącza moduł w wyborze Ustawień. Włączenie zdejmuje moduły, które zastępują
 * CAŁĄ tę samą talię (backend odrzuca dwie talie agend naraz - `core/variants`).
 */
export function toggleVariant(
  current: readonly string[],
  module: VariantModuleInfo,
  on: boolean,
): string[] {
  const rest = current.filter((id) => id !== module.id);
  if (!on) return rest;
  const clashes = (id: string) => {
    const other = moduleById.get(id);
    return !!other && module.wholeDecks.some((kind) => other.wholeDecks.includes(kind));
  };
  return [...rest.filter((id) => !clashes(id)), module.id];
}

/**
 * Id modułów gry z `cardPool`: `variants` z backendu, a dla starszych gier moduł talii
 * agend o źródle `agendaVariant` (np. "absol"). Brak danych = gra bez wariantów.
 */
export function gameVariantIds(
  pool: { variants?: readonly string[]; agendaVariant?: string } | undefined,
): string[] {
  if (pool?.variants) return [...pool.variants];
  const legacy = VARIANT_MODULES.find(
    (m) => m.source === pool?.agendaVariant && m.decks.agenda,
  );
  return legacy ? [legacy.id] : [];
}

/** Moduł gry, który zmienia talię `kind` (pierwszy wg kolejności wyboru) albo `undefined`. */
function deckModule(
  kind: ActiveDeckKind,
  variantIds: readonly string[] | undefined,
): VariantModuleInfo | undefined {
  return (variantIds ?? [])
    .map((id) => moduleById.get(id))
    .find((m): m is VariantModuleInfo => !!m && !!m.decks[kind]);
}

/**
 * Czy karta należy do talii `kind` W TEJ GRZE (moduły `variantIds`), z kontrolą źródła:
 * oficjalne źródło albo źródło modułu, który zmienia tę talię. Bez modułu = `isInActiveDeck`.
 */
export function isInGameDeck(
  kind: ActiveDeckKind,
  alias: string,
  source: string,
  variantIds?: readonly string[],
): boolean {
  const module = deckModule(kind, variantIds);
  if (!module) return isOfficialSource(source) && isInActiveDeck(kind, alias);
  const ids = moduleDeckSets.get(module.id)?.[kind];
  return (isOfficialSource(source) || source === module.source) && !!ids?.has(alias);
}

const badgeBySource = new Map(
  VARIANT_MODULES.filter((m) => m.badge).map((m) => [m.source, m.badge as string]),
);

/** Krótka plakietka źródła fanowskiej karty (np. "ABS" dla Absol); `null` = oficjalna. */
export function fanSourceBadge(source: string | undefined): string | null {
  return (source && badgeBySource.get(source)) || null;
}
