import {
  TILE_HEIGHT,
  TILE_WIDTH,
  calculateStatTilePositions,
} from "@/entities/geometry/tilePositioning";

/** Lewy górny róg tacy efektów w jednostkach planszy (przed skalą zoomu). */
export type ZoneAnchor = { x: number; y: number };

type Box = { left: number; top: number; right: number; bottom: number };

/**
 * Gdzie położyć tacę efektów trwałych: po prawej stronie planszy, w luce między polami
 * graczy (na mapie 6-osobowej - między graczem 2 i 3, pozycja 407). Bierze pola graczy
 * leżące na prawo od środka planszy, sortuje je z góry na dół i wybiera największą
 * pionową lukę; taca zaczyna się na prawej kolumnie tych pól, wyśrodkowana w luce.
 * Bez dwóch pól po prawej - prawa krawędź planszy na wysokości jej środka.
 */
export function effectsZoneAnchor(
  statTilePositions: Record<string, string[]>,
  ringCount: number | undefined,
  tilePositions: string[] | undefined,
): ZoneAnchor | null {
  const areas: Box[] = [];
  for (const positions of Object.values(statTilePositions)) {
    if (positions.length === 0) continue;
    const tiles = calculateStatTilePositions(positions, ringCount, tilePositions);
    areas.push({
      left: Math.min(...tiles.map((t) => t.x)),
      top: Math.min(...tiles.map((t) => t.y)),
      right: Math.max(...tiles.map((t) => t.x + TILE_WIDTH)),
      bottom: Math.max(...tiles.map((t) => t.y + TILE_HEIGHT)),
    });
  }
  if (areas.length === 0) return null;

  const minX = Math.min(...areas.map((a) => a.left));
  const maxX = Math.max(...areas.map((a) => a.right));
  const centreX = (minX + maxX) / 2;
  const right = areas
    .filter((a) => (a.left + a.right) / 2 > centreX)
    .sort((a, b) => a.top - b.top);

  let best: { upper: Box; lower: Box; gap: number } | null = null;
  for (let i = 0; i + 1 < right.length; i++) {
    const gap = right[i + 1].top - right[i].bottom;
    if (!best || gap > best.gap) best = { upper: right[i], lower: right[i + 1], gap };
  }
  if (!best) {
    const minY = Math.min(...areas.map((a) => a.top));
    const maxY = Math.max(...areas.map((a) => a.bottom));
    return { x: maxX - TILE_WIDTH, y: (minY + maxY) / 2 - TILE_HEIGHT / 2 };
  }
  const midY = (best.upper.bottom + best.lower.top) / 2;
  return {
    x: Math.max(best.upper.right, best.lower.right) - TILE_WIDTH,
    y: midY - TILE_HEIGHT / 2,
  };
}
