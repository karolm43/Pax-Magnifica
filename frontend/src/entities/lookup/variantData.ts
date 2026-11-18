/*
 * Dane komponentów zmienionych/dodanych przez MODUŁY WARIANTÓW bieżącej gry (fanowskie
 * zestawy, erraty, własne komponenty) - z backendu `/api/public/game/{id}/variant-data`
 * (`src/core/variants.py`, instrukcja: docs/WARIANTY.md).
 *
 * Statyczne dane frontu (`entities/data/*`) znają tylko oficjalne komponenty. Każda funkcja
 * wyszukująca (`getTechData`, `getRelicData`, `getUnitData`…) nakłada na nie wpis wariantu
 * (`withVariant`): errata zachowuje oficjalne id i podmienia tekst/liczby, nowy komponent
 * istnieje tylko tu. Pule kart (talie) dostają nowe karty przez `withVariantList`.
 */

/** Klucz talii frontu (`ActiveDeckKind` + eksploracja). */
export type VariantDeckKey =
  | "agenda"
  | "actionCard"
  | "relic"
  | "secretObjective"
  | "stage1Objective"
  | "stage2Objective"
  | "explore";

/** Kategoria komponentu (wartości `ComponentCategory` backendu). */
export type VariantCategory =
  | "technologies"
  | "units"
  | "leaders"
  | "abilities"
  | "factions"
  | "breakthroughs"
  | "planets"
  | "strategy_cards"
  | "action_cards"
  | "agendas"
  | "relics"
  | "explores"
  | "promissory_notes"
  | "public_objectives"
  | "secret_objectives"
  | "genericcards";

export type VariantPayload = {
  variants: string[];
  badges: Record<string, string>;
  entries: Partial<Record<string, Record<string, Record<string, unknown>>>>;
  decks: Partial<Record<VariantDeckKey, string[]>>;
};

const EMPTY: VariantPayload = { variants: [], badges: {}, entries: {}, decks: {} };

let current: VariantPayload = EMPTY;
const deckSets = new Map<string, ReadonlySet<string>>();

/** Ustawia dane wariantów bieżącej gry (wołane po pobraniu `/variant-data`). */
export function setVariantData(payload: VariantPayload | null | undefined): void {
  current = payload ?? EMPTY;
  deckSets.clear();
  for (const [key, ids] of Object.entries(current.decks)) {
    if (ids) deckSets.set(key, new Set(ids));
  }
}

/** Dane wariantów bieżącej gry (testy, diagnostyka). */
export function variantData(): VariantPayload {
  return current;
}

/** Surowy wpis wariantu komponentu albo `undefined` (komponent bez zmian). */
export function variantEntry(
  category: VariantCategory,
  id: string,
): Record<string, unknown> | undefined {
  return current.entries[category]?.[id];
}

/**
 * Dane komponentu z nałożonym wariantem gry: errata podmienia pola (id zostaje), nowy
 * komponent wariantu istnieje tylko tu. Bez wariantu - dane statyczne bez zmian.
 */
export function withVariant<T>(
  category: VariantCategory,
  id: string,
  base: T | undefined,
): T | undefined {
  const entry = variantEntry(category, id);
  if (!entry) return base;
  return { ...(base ?? {}), ...entry } as T;
}

/**
 * Lista komponentów kategorii z nałożonymi wariantami + NOWE komponenty wariantów
 * (których nie ma w statycznych danych). `keyOf` = pole id w danych frontu.
 */
export function withVariantList<T>(
  category: VariantCategory,
  list: readonly T[],
  keyOf: (item: T) => string,
): T[] {
  const entries = current.entries[category];
  if (!entries) return [...list];
  const seen = new Set<string>();
  const out = list.map((item) => {
    const key = keyOf(item);
    seen.add(key);
    return withVariant(category, key, item) as T;
  });
  for (const [id, entry] of Object.entries(entries)) {
    if (!seen.has(id)) out.push(entry as T);
  }
  return out;
}

/** Talia gry zastąpiona w całości przez moduł (zbiór id) albo `undefined` = talia oficjalna. */
export function variantDeck(kind: VariantDeckKey): ReadonlySet<string> | undefined {
  return deckSets.get(kind);
}

/** Plakietka źródła modułu gry (np. "BSP") albo `undefined`. */
export function variantBadge(source: string | undefined): string | undefined {
  return source ? current.badges[source] : undefined;
}

/** Źródło wariantu, z którego pochodzi wpis (errata: `variantSource`, nowy: `source`). */
export function variantSourceOf(entry: { source?: string; variantSource?: unknown }): string | undefined {
  return typeof entry.variantSource === "string" ? entry.variantSource : entry.source;
}
