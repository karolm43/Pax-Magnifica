// Frakcje, których technologie startowe NIE są wybierane w setupie, tylko później,
// już w grze (przed pierwszą fazą agendy), po tym jak wszyscy pozostali gracze
// otrzymają swoje technologie startowe.
//
// DWIE takie frakcje (zgodnie z regułą „The Tribunii" Keleresa i „Research Team"
// Deepwrought — patrz docs/rules_tirules/F_keleres.md, F_deepwrought.md oraz
// docs/RULES.md 16):
//   • The Council Keleres (keleresm/keleresx/keleresa) — wybiera DO 2 nie-frakcyjnych
//     technologii POSIADANYCH przez innych graczy; musi poczekać na wszystkich.
//   • The Deepwrought Scholarate (deepwrought) — „research technology twice": wybiera
//     2 dowolne technologie (z początku drzewka), również po pozostałych graczach.
//
// Dla tych frakcji ekran wyboru NIE pokazuje panelu wyboru technologii — zamiast tego
// pokazuje elegancki komunikat, że wybór nastąpi w grze. Powód: Keleres zależy od tego,
// co posiadają INNI gracze (nieznane w setupie), a pełny model takiego odroczonego
// wyboru należy do warstwy silnika (okna czasowe), nie do kreatora setupu.
//
// To świadoma decyzja produktowa warstwy UI (stąd lista po id tutaj, a nie flaga w
// danych AsyncTI4): klasyfikuje, jak setup TRAKTUJE frakcję, a nie jej statyczne dane.

/** Id frakcji z odroczonym (in-game) wyborem technologii startowych. */
const DEFERRED_STARTING_TECH = new Set<string>([
  "keleresm",
  "keleresx",
  "keleresa",
  "deepwrought",
]);

/** Czy frakcja wybiera technologie startowe PÓŹNIEJ (w grze), nie w setupie. */
export function hasDeferredStartingTech(factionId: string): boolean {
  return DEFERRED_STARTING_TECH.has(factionId);
}

/**
 * Komunikat (po angielsku, w tonie planszówki) wyjaśniający odroczony wybór technologii
 * danej frakcji. Zwraca `null`, gdy frakcja nie ma odroczonego wyboru.
 */
export function deferredStartingTechNotice(factionId: string): string | null {
  switch (factionId) {
    case "deepwrought":
      return (
        "During setup, the Scholarate researches two technologies of its choosing. " +
        "This is resolved in play — before the first strategy phase."
      );
    case "keleresm":
    case "keleresx":
    case "keleresa":
      return (
        "The Council claims up to two non-faction technologies already held by rival " +
        "empires. This is resolved in play — before the first strategy phase, once every " +
        "other empire has claimed its starting technology."
      );
    default:
      return null;
  }
}
