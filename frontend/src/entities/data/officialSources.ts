/*
 * Oficjalne, aktywne źródła kart — zgodne z `assets/enabled_sources.json`
 * backendu. Wygenerowane dane frontendu zawierają TĘ SAMĄ kartę z wielu źródeł
 * homebrew (absol, twilights_fall, …) pod różnymi aliasami; bez tego filtra listy
 * (pula kart, edytor gracza) dublowałyby pozycje. Trzymamy oficjalny zestaw:
 * base + pok + codex1–4 + thunders_edge.
 */
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
