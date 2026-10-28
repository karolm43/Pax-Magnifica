/** Fighters and infantry render as a count badge instead of individual units. */
export function isBadgeUnit(unitType: string): unitType is "ff" | "gf" {
  return unitType === "ff" || unitType === "gf";
}

/**
 * Statki (asyncId) stojące w PRZESTRZENI. Spójne z backendowym
 * ``PLACEMENT_BY_BASE_TYPE`` (RULES.md 2b/26): statki tylko w orbicie, siły
 * naziemne/struktury (gf, mf, pd, sd) tylko na planecie.
 */
const SHIP_ASYNC_IDS = new Set(["ff", "dd", "ca", "cv", "dn", "fs", "ws"]);

/** Czy jednostka (po asyncId) jest statkiem (stoi w przestrzeni, nie na planecie). */
export function isShipUnit(asyncId: string): boolean {
  return SHIP_ASYNC_IDS.has(asyncId);
}
