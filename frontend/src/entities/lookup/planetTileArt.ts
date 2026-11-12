import { getTileById } from "@/entities/lookup/systems";
import { getPlanetLocalPosition } from "@/entities/lookup/planets";
import { assetUrl } from "@/shared/assets/resolveAsset";
import type { Planet, Point } from "@/entities/data/types";
import measuredRadius from "@/entities/data/planetArtRadius.json";

/** Rozmiar grafiki kafelka (px), w którym liczone są pozycje planet. */
export const TILE_ART_WIDTH = 345;
export const TILE_ART_HEIGHT = 299;
/**
 * Promień zwykłej planety na kafelku (px). Duże planety (Mecatol, legendarne, Thunder's Edge)
 * mają promień zmierzony z grafiki (`planetArtRadius.json`, `scripts/measure_planet_radius.py`).
 */
export const DEFAULT_PLANET_RADIUS = 60;

const MEASURED: Readonly<Record<string, number>> = measuredRadius;

/**
 * Grafika planety wycinana z jej kafelka: adres obrazka, środek planety na kafelku
 * i jej promień. Planety rzadko leżą na środku heksa, więc kadr zawsze liczymy od
 * `centerPosition` (albo `positionInTile`). Promień: `planetRadius` z danych, potem pomiar
 * z grafiki, potem standard. `null` - planeta bez kafelka/pozycji.
 */
export function getPlanetTileArt(
  planet: Planet,
): { src: string; center: Point; radius: number } | null {
  if (!planet.tileId) return null;
  const tile = getTileById(planet.tileId);
  const center = getPlanetLocalPosition(planet);
  if (!tile || !center) return null;
  return {
    src: assetUrl(`/tiles/${tile.imagePath}`),
    center,
    radius:
      planet.planetLayout?.planetRadius ||
      MEASURED[planet.id] ||
      DEFAULT_PLANET_RADIUS,
  };
}
