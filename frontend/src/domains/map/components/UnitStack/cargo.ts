/**
 * Wspólne mapowania jednostek dla ruchu taktycznego (statek vs ładunek) + tłumaczenie
 * asyncId → baseType. Reużywane przez drag&drop (``useUnitDrag``) i okno ruchu
 * (``MovementStepPanel``), żeby klasyfikacja była w JEDNYM miejscu (spójna z backendem
 * ``ASYNC_ID_BY_BASE_TYPE`` / ``PLACEMENT_BY_BASE_TYPE``).
 */

/* asyncId → baseType (ten sam zbiór co backend). Tłumaczenie identyfikatorów, nie reguła. */
export const BASE_TYPE_BY_ASYNC: Record<string, string> = {
  ff: "fighter",
  dd: "destroyer",
  ca: "cruiser",
  cv: "carrier",
  dn: "dreadnought",
  fs: "flagship",
  ws: "warsun",
  gf: "infantry",
  mf: "mech",
  pd: "pds",
  sd: "spacedock",
};

/* Statki ruszające o WŁASNYM ruchu (bez myśliwca — ten jedzie jako ładunek). */
export const SHIP_ONLY_ASYNC = new Set(["dd", "ca", "cv", "dn", "fs", "ws"]);

/* Ładunek transportu: myśliwce + siły naziemne (RULES.md 32.3). */
export const CARGO_ASYNC = new Set(["ff", "gf", "mf"]);

/** baseType dla asyncId (fallback: sam asyncId, gdy nieznany). */
export function baseTypeOf(asyncId: string): string {
  return BASE_TYPE_BY_ASYNC[asyncId] ?? asyncId;
}

/** Czy dana jednostka (asyncId) jedzie jako ŁADUNEK w ruchu taktycznym. */
export function isCargoUnit(asyncId: string): boolean {
  return CARGO_ASYNC.has(asyncId);
}

/* Struktury (asyncId) — NIE przewożą jednostek, mimo że w danych mają capacity
   (space dock daje „capacity" dla reguł floty/produkcji, nie dla transportu). */
export const STRUCTURE_ASYNC = new Set(["sd", "pd"]);

/** Czy jednostka (asyncId) to STRUKTURA (space dock / PDS) — nie nosiciel transportu. */
export function isStructureUnit(asyncId: string): boolean {
  return STRUCTURE_ASYNC.has(asyncId);
}
