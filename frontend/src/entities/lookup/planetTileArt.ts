import { getTileById } from "@/entities/lookup/systems";
import { getPlanetLocalPosition } from "@/entities/lookup/planets";
import { assetUrl } from "@/shared/assets/resolveAsset";
import type { Planet, Point } from "@/entities/data/types";

/** Rozmiar grafiki kafelka (px), w którym liczone są pozycje planet. */
export const TILE_ART_WIDTH = 345;
export const TILE_ART_HEIGHT = 299;
/** Typowy promień planety na kafelku (px), gdy dane nie podają `planetRadius`. */
export const DEFAULT_PLANET_RADIUS = 50;

/**
 * Grafika planety wycinana z jej kafelka: adres obrazka, środek planety na kafelku
 * i jej promień. Planety rzadko leżą na środku heksa, więc kadr zawsze liczymy od
 * `centerPosition` (albo `positionInTile`). `null` - planeta bez kafelka/pozycji.
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
    radius: planet.planetLayout?.planetRadius || DEFAULT_PLANET_RADIUS,
  };
}
