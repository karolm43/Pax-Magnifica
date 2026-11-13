// TYMCZASOWE (decyzja użytkownika 2026-11-13) — DO USUNIĘCIA, gdy wszystkie frakcje będą gotowe.
//
// Kreator (także lobby sieciowe) pokazuje i losuje WYŁĄCZNIE frakcje ukończone w silniku
// (komplet komponentów: test `missing_components(...) == []` + scenariusze w
// `tests/factions/test_flows_<frakcja>.py`). Usunięcie: skasuj ten plik i jego dwa użycia
// w `SetupWizard.tsx` (filtr listy + rozwiązanie „Random" przed wysyłką).
import type { FactionInfo } from "@/api/useNewGame";

/** Frakcje ukończone (Fala 1, PLAN_FRAKCJE B1–B4). Dopisuj kolejne po ich domknięciu. */
export const TEMP_READY_FACTION_IDS: ReadonlySet<string> = new Set([
  "sardakk",
  "letnev",
  "jolnar",
  "sol",
  "arborec",
  "hacan",
  "winnu",
]);

/** Lista frakcji zawężona do gotowych (tymczasowo). */
export function tempReadyFactions(factions: readonly FactionInfo[]): FactionInfo[] {
  return factions.filter((f) => TEMP_READY_FACTION_IDS.has(f.id));
}
