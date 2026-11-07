import { lookupUnit } from "@/entities/lookup/units";
import type { PlayerData } from "@/entities/data/types";
import { isCargoUnit, isStructureUnit } from "./cargo";

/** Zaznaczenie wielu jednostek (Ctrl+klik) — kształt jak ``AppStore["multiSelect"]``. */
export type MultiSelection = {
  fromPosition: string;
  faction: string;
  items: Record<string, { asyncId: string; fromZone: string; count: number }>;
};

/** Sumy zaznaczenia: pojemność nosicieli vs zajęcie ładunkiem + liczba sztuk. */
export type SelectionSummary = {
  total: number; // wszystkich zaznaczonych sztuk
  capacity: number; // suma capacity zaznaczonych statków-nosicieli
  used: number; // zaznaczony ładunek (myśliwce + siły naziemne)
};

/**
 * Liczy capacity zaznaczenia. Capacity bierze z danych jednostki (z uwzględnieniem
 * ulepszeń gracza) — to tylko podgląd dla gracza; legalność egzekwuje backend.
 */
export function summarizeSelection(
  sel: MultiSelection,
  players: PlayerData[] | undefined,
): SelectionSummary {
  const player = players?.find((p) => p.faction === sel.faction);
  let total = 0;
  let capacity = 0;
  let used = 0;
  for (const item of Object.values(sel.items)) {
    total += item.count;
    if (isCargoUnit(item.asyncId)) {
      used += item.count;
      continue;
    }
    if (isStructureUnit(item.asyncId)) continue;
    const unit = lookupUnit(item.asyncId, sel.faction, player);
    capacity += (unit?.capacityValue ?? 0) * item.count;
  }
  return { total, capacity, used };
}
