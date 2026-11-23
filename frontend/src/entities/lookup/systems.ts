import { systems } from "@/entities/data/systems";
import type { TileData } from "@/entities/data/types";

const tilesById = new Map<string, TileData>();
for (const tile of systems) {
  if (!tilesById.has(tile.id)) tilesById.set(tile.id, tile);
}

export function getTileById(tileId: string): TileData | undefined {
  return tilesById.get(tileId);
}

/**
 * Etykieta systemu dla gracza: pełna nazwa z danych + pozycja na mapie, np.
 * „Mecatol Rex (000)”. Bez nazwy w danych — „System 103”.
 */
export function systemDisplayName(systemId: string | undefined, position: string): string {
  const name = systemId ? getTileById(systemId)?.name : undefined;
  return name && name !== "None" ? `${name} (${position})` : `System ${position}`;
}
