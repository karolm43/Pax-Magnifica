import { HEX_PATH, TILE_HEIGHT, TILE_WIDTH } from "./tilePositioning";
import { SPIRAL_TILE_OUTLINES } from "./tileOutlines.generated";

/** Kształt kafla systemu we współrzędnych kafla (lewy górny róg grafiki = 0,0). */
export type TileOutline = {
  /** Rozmiar obszaru rysowania obrysu (= rozmiar grafiki kafla). */
  width: number;
  height: number;
  /** Ścieżka SVG obrysu: heks albo kontur nieregularnej grafiki. */
  path: string;
  /** Środek kształtu (punkt docelowy linii wormhole, środek podświetleń). */
  center: { x: number; y: number };
  /** True dla kafli o kształcie innym niż heks (Creuss, Crimson, Mallice…). */
  irregular: boolean;
};

const HEX_OUTLINE: TileOutline = {
  width: TILE_WIDTH,
  height: TILE_HEIGHT,
  path: HEX_PATH,
  center: { x: TILE_WIDTH / 2, y: TILE_HEIGHT / 2 },
  irregular: false,
};

/**
 * Obrys systemu do hit-targetu i podświetleń. Kafle „spiralne” (AsyncTI4 TYPE09/12/15:
 * Creuss, Crimson, Mallice, Kwon, Ethan) mają grafikę ok. 416x386 rysowaną od lewego
 * górnego rogu — heks 345x299 w tym samym miejscu nie pokrywał ich kształtu (klik obok
 * kształtu trafiał, klik w jego dolną-prawą część nie). Obrys jest konturem kanału alfa
 * (``scripts/gen_tile_outlines.py``); środek = środek grafiki (Java: heks anomalii
 * kafla spiralnego rysowany z przesunięciem +36,+43 = ten sam środek).
 */
export function tileOutline(systemId: string | undefined): TileOutline {
  const spiral = systemId ? SPIRAL_TILE_OUTLINES[systemId.toLowerCase()] : undefined;
  if (!spiral) return HEX_OUTLINE;
  return {
    ...spiral,
    center: { x: spiral.width / 2, y: spiral.height / 2 },
    irregular: true,
  };
}
