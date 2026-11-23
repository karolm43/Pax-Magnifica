import {
  TILE_HEIGHT,
  TILE_WIDTH,
  calculateStatTilePositions,
} from "@/entities/geometry/tilePositioning";

/** Lewy górny róg pierwszego heksa tacy efektów w jednostkach planszy (przed skalą zoomu). */
export type ZoneAnchor = { x: number; y: number };
export type ZoneSide = "left" | "right";

/** Odstęp tacy od najdalszego heksa, gdy nie ma wolnej komórki siatki (jednostki planszy). */
export const ZONE_GAP = 60;

/** Krok siatki heksów: kolejna kolumna = +260 w poziomie i ±150 w pionie (jak plansza). */
export const LATTICE_DX = 260;
export const LATTICE_DY = 150;

type Box = { left: number; top: number; right: number; bottom: number };
type Point = { x: number; y: number };

/**
 * Gdzie położyć tacę efektów trwałych: heks na siatce planszy, po prawej stronie, w luce
 * między polami graczy (na mapie 6-osobowej - wolna komórka 407 między graczem 2 i 3).
 * Bierze pola graczy leżące na prawo od środka planszy, sortuje je z góry na dół i wybiera
 * największą pionową lukę. Gdy luka mieści heks, a komórka nie jest zajęta przez kafel planszy
 * (`occupied` - lewe górne rogi kafli), taca leży W niej, równo z polami graczy (decyzja
 * użytkownika 2026-11-23: taca ma pasować do planszy). Inaczej - za prawą krawędzią planszy.
 */
export function effectsZoneAnchor(
  statTilePositions: Record<string, string[]>,
  ringCount: number | undefined,
  tilePositions: string[] | undefined,
  /** Lewe górne rogi kafli planszy (np. narożniki poza planszą) - komórka tacy musi być wolna. */
  occupied: Point[] = [],
  /** Strona planszy: efekty po prawej, prawa (lustrzanie) po lewej. */
  side: ZoneSide = "right",
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
  const left = side === "left";
  const right = areas
    .filter((a) => ((a.left + a.right) / 2 > centreX) !== left)
    .sort((a, b) => a.top - b.top);

  let best: { upper: Box; lower: Box; gap: number } | null = null;
  for (let i = 0; i + 1 < right.length; i++) {
    const gap = right[i + 1].top - right[i].bottom;
    if (!best || gap > best.gap) best = { upper: right[i], lower: right[i + 1], gap };
  }

  const free = (cell: Point) =>
    occupied.every((t) => Math.hypot(t.x - cell.x, t.y - cell.y) >= TILE_HEIGHT);
  const boardRight = Math.max(maxX, ...occupied.map((t) => t.x + TILE_WIDTH));
  const boardLeft = Math.min(minX, ...occupied.map((t) => t.x));

  if (best && best.gap >= TILE_HEIGHT - 1) {
    const cell = {
      x: left
        ? Math.min(best.upper.left, best.lower.left)
        : Math.max(best.upper.right, best.lower.right) - TILE_WIDTH,
      y: Math.round((best.upper.bottom + best.lower.top) / 2 - TILE_HEIGHT / 2),
    };
    if (free(cell)) return cell;
  }
  const x = left ? boardLeft - ZONE_GAP - TILE_WIDTH : boardRight + ZONE_GAP;
  if (!best) {
    const minY = Math.min(...areas.map((a) => a.top));
    const maxY = Math.max(...areas.map((a) => a.bottom));
    return { x, y: (minY + maxY) / 2 - TILE_HEIGHT / 2 };
  }
  const midY = (best.upper.bottom + best.lower.top) / 2;
  return { x, y: midY - TILE_HEIGHT / 2 };
}

/** Na jednym heksie tacy mieści się tyle żetonów efektów (2 rzędy po 3). */
export const EFFECTS_PER_HEX = 6;

/**
 * Komórki tacy (względem jej lewego górnego rogu): pierwsza w kotwicy, kolejne w stronę od planszy (prawo/lewo) po
 * siatce planszy (zygzak +260 / +150), gdy efektów jest więcej niż mieści jeden heks.
 */
export function zoneCells(effectCount: number, side: ZoneSide = "right"): Point[] {
  const count = Math.max(1, Math.ceil(effectCount / EFFECTS_PER_HEX));
  const dir = side === "left" ? -1 : 1;
  return Array.from({ length: count }, (_, k) => ({
    x: k === 0 ? 0 : k * LATTICE_DX * dir,
    y: (k % 2) * LATTICE_DY,
  }));
}
