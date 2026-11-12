import type { CSSProperties } from "react";
import type { Planet } from "@/entities/data/types";
import {
  getPlanetTileArt,
  TILE_ART_HEIGHT,
  TILE_ART_WIDTH,
} from "@/entities/lookup/planetTileArt";

const FOCAL_Y_PERCENT = 26;

export function getPlanetTileBackground(planetData: Planet) {
  const art = getPlanetTileArt(planetData);
  if (!art) return null;
  const { center } = art;

  const planetRadius = planetData.planetLayout?.planetRadius ?? 0;
  const focusRadius = Math.max(
    26,
    Math.min(54, (planetRadius || 52) * 0.78)
  );
  const focusFade = Math.max(18, focusRadius * 0.55);
  const focusMid = focusRadius + focusFade * 0.55;
  const focusOuter = focusRadius + focusFade;

  return {
    src: art.src,
    imageStyle: {
      width: TILE_ART_WIDTH,
      height: TILE_ART_HEIGHT,
      left: `calc(50% - ${center.x}px)`,
      top: `calc(${FOCAL_Y_PERCENT}% - ${center.y}px)`,
    } as CSSProperties,
    maskStyle: {
      "--planet-focus-y": `${FOCAL_Y_PERCENT}%`,
      "--planet-focus-radius": `${focusRadius}px`,
      "--planet-focus-mid": `${focusMid}px`,
      "--planet-focus-outer": `${focusOuter}px`,
    } as CSSProperties,
  };
}
