/*
 * Oficjalne, aktywne źródła kart — zgodne z `assets/enabled_sources.json`
 * backendu. Wygenerowane dane frontendu zawierają TĘ SAMĄ kartę z wielu źródeł
 * homebrew (absol, twilights_fall, …) pod różnymi aliasami; bez tego filtra listy
 * (pula kart, edytor gracza) dublowałyby pozycje. Trzymamy oficjalny zestaw:
 * base + pok + codex1–4 + thunders_edge.
 */
import {
  ACTIVE_DECK_IDS,
  AGENDA_VARIANT_DECK_IDS,
  type ActiveDeckKind,
  type AgendaVariant,
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

// FAN-AGENDAS: fanowska talia agend (Absol) wybrana w Ustawieniach - wyjątek od
// OFFICIAL_SOURCES, tylko dla agend. Opis decyzji: `src/core/sources.py`.
const agendaVariantSets: Record<AgendaVariant, ReadonlySet<string>> = {
  absol: new Set(AGENDA_VARIANT_DECK_IDS.absol),
};

/** Czy `variant` to znana fanowska talia agend (np. "absol"); "standard" → false. */
export function isAgendaVariant(variant: string | undefined): variant is AgendaVariant {
  return !!variant && variant in agendaVariantSets;
}

/**
 * Czy agenda należy do talii agend gry. `variant` = `cardPool.agendaVariant` z backendu:
 * "standard" (lub brak) → talia aktywnych źródeł, inaczej wskazana talia fanowska.
 */
export function isInAgendaDeck(variant: string | undefined, alias: string): boolean {
  return isAgendaVariant(variant)
    ? agendaVariantSets[variant].has(alias)
    : activeDeckSets.agenda.has(alias);
}

/** Krótka plakietka źródła fanowskiej karty (np. "ABS" dla Absol); `null` = oficjalna. */
export function fanSourceBadge(source: string | undefined): string | null {
  return source === "absol" ? "ABS" : null;
}
