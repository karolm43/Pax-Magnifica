/*
 * Oficjalne, aktywne źródła kart — zgodne z `assets/enabled_sources.json`
 * backendu. Wygenerowane dane frontendu zawierają TĘ SAMĄ kartę z wielu źródeł
 * homebrew (absol, twilights_fall, …) pod różnymi aliasami; bez tego filtra listy
 * (pula kart, edytor gracza) dublowałyby pozycje. Trzymamy oficjalny zestaw:
 * base + pok + codex1–4 + thunders_edge.
 */
import { ACTIVE_DECK_IDS, type ActiveDeckKind } from "./activeDecks";

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
