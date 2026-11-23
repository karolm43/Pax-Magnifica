// Miejsca przy stole z własnego map stringa (gotowa mapa z domami, np. z draftu Milty).
//
// Backend (`GET /map/seats`, `core/map_string.map_seats`) mówi, na których pozycjach leżą
// kafelki domowe i czyje. Tu układamy to wg miejsc kreatora (`/engine/config` → `seats`):
// `seatFactions[seat]` = frakcja domu na miejscu albo `null`. Mapa domyślna / losowa nie
// ma domów (`seatFactions === null`).

import { useMemo } from "react";
import { useEngineConfig, useMapSeats } from "@/api/useNewGame";
import { RANDOM_MAP, useSetupStore, validateMapString } from "./useSetupStore";

export interface MapSeatInfo {
  /** Frakcja domu na każdym miejscu (indeks = `SetupSlot.seat`); `null` = mapa bez domów. */
  seatFactions: (string | null)[] | null;
  /** Kafelki spoza aktywnych źródeł (gra by ich nie położyła). */
  unknownTiles: string[];
}

export function useMapSeatInfo(): MapSeatInfo {
  const mapString = useSetupStore((s) => s.mapString);
  const trimmed = mapString.trim().replace(/\s+/g, " ");
  const custom =
    trimmed.length > 0 && trimmed !== RANDOM_MAP && validateMapString(trimmed) === null
      ? trimmed
      : null;
  const { data: engineConfig } = useEngineConfig();
  const { data } = useMapSeats(custom);

  return useMemo(() => {
    if (!custom || !data) return { seatFactions: null, unknownTiles: [] };
    const byPosition = new Map(data.seats.map((s) => [s.position, s.faction_id]));
    const seatFactions = (engineConfig?.seats ?? []).map((p) => byPosition.get(p) ?? null);
    return {
      seatFactions: seatFactions.some((f) => f !== null) ? seatFactions : null,
      unknownTiles: data.unknown_tiles,
    };
  }, [custom, data, engineConfig]);
}
