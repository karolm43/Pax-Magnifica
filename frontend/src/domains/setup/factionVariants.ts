// Grupowanie wariantów jednej frakcji w POJEDYNCZĄ pozycję listy wyboru.
//
// Keleres jest w backendzie trzema osobnymi, grywalnymi frakcjami (keleresm/keleresx/
// keleresa — Mentak/Xxcha/Argent). Na liście wyboru nie chcemy trzech wpisów: pokazujemy
// JEDNĄ pozycję „Keleres" z przyciskiem cyklującym po wariantach (podobnie jak podgląd
// Obsidianu przy Firmamencie). Ta sama tożsamość wariantu nadal jest tym, co zapisujemy
// do slotu gracza — cykl zmienia tylko, który wariant jest aktywny.
//
// Logika jest czysta (bez Reacta), więc daje się testować i trzymać z dala od komponentu.

import type { FactionInfo } from "@/api/useNewGame";

/**
 * Rodziny wariantów: krótka nazwa rodziny → uporządkowana lista id wariantów.
 * Kolejność wyznacza kierunek cyklu (Mentak → Xxcha → Argent → Mentak…).
 * Rozszerzalne, gdyby doszły kolejne frakcje o wariantach z jednym wpisem na liście.
 */
export const VARIANT_FAMILIES: Record<string, readonly string[]> = {
  keleres: ["keleresm", "keleresx", "keleresa"],
};

/** Etykieta pozycji listy dla rodziny (jedna, wspólna nazwa bez sufiksu wariantu). */
export const FAMILY_LABEL: Record<string, string> = {
  keleres: "The Council Keleres",
};

/**
 * Krótka etykieta pojedynczego wariantu (sufiks odróżniający), np. „Mentak".
 * Służy do podpisu na przycisku cyklu; pełna nazwa wariantu bywa długa.
 */
export const VARIANT_LABEL: Record<string, string> = {
  keleresm: "Mentak",
  keleresx: "Xxcha",
  keleresa: "Argent",
};

/** Odwrotna mapa: id wariantu → klucz rodziny. Zbudowana raz z `VARIANT_FAMILIES`. */
const FAMILY_OF_VARIANT: Record<string, string> = Object.fromEntries(
  Object.entries(VARIANT_FAMILIES).flatMap(([family, ids]) =>
    ids.map((id) => [id, family]),
  ),
);

/** Klucz rodziny wariantów dla danego id frakcji albo `null`, gdy nie jest wariantem. */
export function familyOfVariant(factionId: string): string | null {
  return FAMILY_OF_VARIANT[factionId] ?? null;
}

/** Czy dane id frakcji należy do rodziny wariantów (jest „cyklowane" na liście). */
export function isVariant(factionId: string): boolean {
  return factionId in FAMILY_OF_VARIANT;
}

/**
 * Następny wariant w cyklu rodziny (zapętlony). Gdy `current` nie należy do rodziny,
 * zwraca pierwszy wariant — bezpieczny start dla pustego/niezgodnego wejścia.
 */
export function nextVariant(family: string, current: string): string {
  const ids = VARIANT_FAMILIES[family] ?? [];
  if (ids.length === 0) return current;
  const idx = ids.indexOf(current);
  return ids[(idx + 1) % ids.length];
}

/** Pierwszy (domyślny) wariant rodziny — pokazywany, zanim gracz zacznie cyklować. */
export function firstVariant(family: string): string {
  const ids = VARIANT_FAMILIES[family] ?? [];
  return ids[0] ?? family;
}

/**
 * Pojedyncza pozycja listy wyboru: albo zwykła frakcja, albo rodzina wariantów.
 * Rodzina niesie listę wariantów i ich definicje (dla ikon/przełącznika), ale na liście
 * zajmuje JEDEN wiersz; wariant przełącza się w panelu szczegółów.
 */
export type FactionListEntry =
  | { kind: "single"; faction: FactionInfo }
  | { kind: "family"; family: string; label: string; variants: FactionInfo[] };

/**
 * Zwija listę frakcji do pozycji listy: warianty tej samej rodziny scala w jeden wpis
 * „family" (pojawia się w miejscu PIERWSZEGO napotkanego wariantu, zachowując sortowanie
 * wejścia). Pozostałe frakcje przechodzą jako „single".
 */
export function collapseVariants(factions: FactionInfo[]): FactionListEntry[] {
  const entries: FactionListEntry[] = [];
  const familyIndex = new Map<string, number>(); // family → indeks w `entries`

  for (const faction of factions) {
    const family = familyOfVariant(faction.id);
    if (family === null) {
      entries.push({ kind: "single", faction });
      continue;
    }
    const existing = familyIndex.get(family);
    if (existing === undefined) {
      familyIndex.set(family, entries.length);
      entries.push({
        kind: "family",
        family,
        label: FAMILY_LABEL[family] ?? family,
        variants: [faction],
      });
    } else {
      const entry = entries[existing];
      if (entry.kind === "family") entry.variants.push(faction);
    }
  }

  // Warianty w każdej rodzinie w kanonicznej kolejności (nie w kolejności wejścia).
  for (const entry of entries) {
    if (entry.kind === "family") {
      const order = VARIANT_FAMILIES[entry.family] ?? [];
      entry.variants.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
    }
  }

  return entries;
}

// ── Grupowanie wg dodatków (Base Game / Prophecy of Kings / Thunder's Edge) ─────────

/**
 * Klucze grup dodatków — stały, uporządkowany zbiór. Kolejność wyznacza kolejność
 * sekcji na liście wyboru.
 */
export const EXPANSION_ORDER = ["base", "pok", "thunders_edge"] as const;
export type ExpansionGroup = (typeof EXPANSION_ORDER)[number];

/** Czytelna nazwa sekcji dodatku. */
export const EXPANSION_LABEL: Record<ExpansionGroup, string> = {
  base: "Base Game",
  pok: "Prophecy of Kings",
  thunders_edge: "Thunder's Edge",
};

/**
 * Mapuje źródło frakcji (`FactionInfo.source`) na grupę dodatku. Keleres ma w danych
 * źródło „codex3", ale na życzenie trafia do Thunder's Edge — tak jak wszystkie źródła
 * spoza base/pok (codexy, thunders_edge). Nieznane/puste → Thunder's Edge (najnowszy
 * worek), by nic nie wypadło z listy.
 */
export function expansionGroup(source: string): ExpansionGroup {
  if (source === "base") return "base";
  if (source === "pok") return "pok";
  return "thunders_edge";
}

/** Sekcja listy: etykieta dodatku + jej pozycje (zwinięte warianty). */
export type ExpansionSection = {
  group: ExpansionGroup;
  label: string;
  entries: FactionListEntry[];
};

/**
 * Buduje sekcje listy wyboru: najpierw zwija warianty (Keleres → jeden wpis), potem
 * rozdziela wpisy na grupy dodatków w stałej kolejności. Grupa wariantu jest wyznaczana
 * ze źródła PIERWSZEGO wariantu (wszystkie Keleres mają to samo źródło). Puste grupy
 * pomijane.
 */
export function groupByExpansion(factions: FactionInfo[]): ExpansionSection[] {
  const entries = collapseVariants(factions);
  const buckets = new Map<ExpansionGroup, FactionListEntry[]>();

  for (const entry of entries) {
    const source =
      entry.kind === "single"
        ? entry.faction.source
        : (entry.variants[0]?.source ?? "");
    const group = expansionGroup(source);
    const list = buckets.get(group) ?? [];
    list.push(entry);
    buckets.set(group, list);
  }

  return EXPANSION_ORDER.filter((g) => (buckets.get(g)?.length ?? 0) > 0).map(
    (group) => ({
      group,
      label: EXPANSION_LABEL[group],
      entries: buckets.get(group) ?? [],
    }),
  );
}
