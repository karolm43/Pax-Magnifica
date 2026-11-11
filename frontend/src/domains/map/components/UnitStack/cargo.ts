/**
 * Wspólne mapowania jednostek dla ruchu taktycznego (statek vs ładunek) + tłumaczenie
 * asyncId → baseType. Reużywane przez drag&drop (``useUnitDrag``) i okno ruchu
 * (``MovementStepPanel``), żeby klasyfikacja była w JEDNYM miejscu (spójna z backendem
 * ``ASYNC_ID_BY_BASE_TYPE`` / ``PLACEMENT_BY_BASE_TYPE``).
 */

import { lookupUnit } from "@/entities/lookup/units";
import type { PlayerData } from "@/entities/data/types";

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

/** Czy dana jednostka (asyncId) MOŻE jechać jako ładunek (myśliwiec, piechota, mech). */
export function isCargoUnit(asyncId: string): boolean {
  return CARGO_ASYNC.has(asyncId);
}

/**
 * Czy jednostka gracza ma WŁASNY ruch wg jego wariantu (dane, nie lista na sztywno): statki
 * zawsze, a myśliwiec dopiero z Fighter II (Move 2, "may move without being transported").
 */
export function isSelfMoving(asyncId: string, faction: string, player?: PlayerData): boolean {
  if (SHIP_ONLY_ASYNC.has(asyncId)) return true;
  if (asyncId !== "ff") return false;
  return (lookupUnit(asyncId, faction, player)?.moveValue ?? 0) > 0;
}

/**
 * Czy jednostka jedzie w ruchu taktycznym JAKO ŁADUNEK (wymaga nosiciela). Myśliwiec z
 * Fighter II ma własny ruch, więc rusza sam; nadal wolno go załadować na nosiciela.
 */
export function movesAsCargo(asyncId: string, faction: string, player?: PlayerData): boolean {
  return CARGO_ASYNC.has(asyncId) && !isSelfMoving(asyncId, faction, player);
}

/* Struktury (asyncId) — NIE przewożą jednostek, mimo że w danych mają capacity
   (space dock daje „capacity" dla reguł floty/produkcji, nie dla transportu). */
export const STRUCTURE_ASYNC = new Set(["sd", "pd"]);

/** Czy jednostka (asyncId) to STRUKTURA (space dock / PDS) — nie nosiciel transportu. */
export function isStructureUnit(asyncId: string): boolean {
  return STRUCTURE_ASYNC.has(asyncId);
}
