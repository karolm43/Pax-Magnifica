import { getTileById } from "@/entities/lookup/systems";
import { getTokenData } from "@/entities/lookup/tokens";

/**
 * Where wormholes and Fracture gates sit on the board: printed on tile art (shared by the
 * Travel Ban marker, wormhole hover hotspots and the flight replay) and carried by tokens.
 */

/** Link kinds a token carries (empty = the token links nothing). */
export function linkKindsOfToken(tokenId: string): string[] {
  if (tokenId === "ingress") return ["INGRESS"];
  if (tokenId === "egress") return ["EGRESS"];
  return (getTokenData(tokenId)?.wormholes ?? []).map((w) => w.toUpperCase());
}

type Point = { x: number; y: number };

type WormholeKey = "alpha" | "beta" | "gamma" | "delta" | "epsilon";

/**
 * Per-tile wormhole art positions, ported from TileGenerator.java drawOnWormhole
 * (lewy górny róg znacznika 80x80; środek nadruku = punkt + 40). Gamma/delta/epsilon na
 * kaflach spiralnych (Creuss, Crimson, Mallice) zmierzone z grafik — Java ich nie ma, a
 * domyślny punkt wypadał poza nadrukiem.
 */
const TILE_WORMHOLE_POSITIONS: Record<string, Partial<Record<WormholeKey, Point>>> = {
  "51": { delta: { x: 233, y: 245 } }, // Creuss home
  "118": { epsilon: { x: 243, y: 241 } }, // Crimson home
  "82a": { gamma: { x: 173, y: 278 } }, // locked nexus
  "82b": { alpha: { x: 95, y: 249 }, beta: { x: 169, y: 273 }, gamma: { x: 240, y: 253 } }, // wormhole nexus
  c02: { alpha: { x: 37, y: 158 }, beta: { x: 223, y: 62 } }, // Locke/Bentham
  c10: { alpha: { x: 182, y: 22 }, beta: { x: 259, y: 241 } }, // Kwon
  c11: { alpha: { x: 54, y: 138 }, beta: { x: 159, y: 275 } }, // Ethan
  d119: { beta: { x: 94, y: 170 } }, // beta/nebula
  d123: { alpha: { x: 22, y: 110 }, beta: { x: 190, y: 206 } }, // alpha/beta/supernova
  er19: { alpha: { x: 60, y: 44 }, beta: { x: 192, y: 184 } }, // alpha/beta/rift
  er119: { alpha: { x: 60, y: 44 }, beta: { x: 192, y: 184 } }, // alpha/beta/nebula
  er94: { beta: { x: 157, y: 165 } }, // Iynntani
  er95: { alpha: { x: 60, y: 155 }, beta: { x: 215, y: 61 } }, // Kytos/Prymis
  m05: { alpha: { x: 185, y: 180 } }, // Shanh
  m32: { beta: { x: 49, y: 147 } }, // Vespa/Apis
};

/** Fallback positions by ship-position layout, from ShipPositionModel.java getWormholeLocation. */
const SHIP_POSITION_WORMHOLE: Record<string, Point> = {
  TYPE05: { x: 162, y: 166 }, // planet and wormhole
  TYPE07: { x: 172, y: 32 }, // 1 planet bottom left
  TYPE08: { x: 132, y: 110 }, // empty and wormhole
  TYPE13: { x: 139, y: 186 }, // Eko
  TYPE14: { x: 152, y: 124 }, // Horace
};

export function getWormholeCoordinates(
  tileId: string,
  shipPositionsType: string | null | undefined,
  hasAlpha: boolean,
  hasBeta: boolean,
  offset: number,
): Point[] {
  const shift = (point: Point) => ({ x: offset + point.x, y: offset + point.y });
  const tilePositions = TILE_WORMHOLE_POSITIONS[tileId];

  if (tilePositions) {
    return [
      hasAlpha && tilePositions.alpha,
      hasBeta && tilePositions.beta,
    ]
      .filter((point): point is Point => !!point)
      .map(shift);
  }

  const layoutPosition = shipPositionsType
    ? SHIP_POSITION_WORMHOLE[shipPositionsType]
    : undefined;
  const point = layoutPosition
    ? shift(layoutPosition)
    : { x: offset + 86, y: 260 };
  return [hasAlpha && point, hasBeta && point].filter(
    (p): p is Point => !!p,
  );
}

/**
 * Środki nadruków wormhole / egress na grafice kafelka (współrzędne kafelka). Ta sama
 * tabela pozycji co znacznik Travel Ban; kilka rodzajów w jednym miejscu = jeden punkt.
 */
export function getPrintedLinkPoints(
  systemId: string,
): { x: number; y: number; kinds: string[] }[] {
  const systemData = getTileById(systemId);
  if (!systemData) return [];
  const kinds = (systemData.wormholes ?? [])
    .filter((w): w is string => !!w)
    .map((w) => w.toUpperCase());
  if (systemData.hasEgress) kinds.push("EGRESS");

  const offset = 40;
  const tilePositions = TILE_WORMHOLE_POSITIONS[systemId];
  const layoutPosition = systemData.shipPositionsType
    ? SHIP_POSITION_WORMHOLE[systemData.shipPositionsType]
    : undefined;
  const fallback = layoutPosition ?? { x: 86, y: 220 };

  const points = new Map<string, { x: number; y: number; kinds: string[] }>();
  for (const kind of new Set(kinds)) {
    const own = tilePositions?.[kind.toLowerCase() as WormholeKey];
    const base = own ?? fallback;
    const key = `${base.x},${base.y}`;
    const point = points.get(key) ?? { x: offset + base.x, y: offset + base.y, kinds: [] };
    point.kinds.push(kind);
    points.set(key, point);
  }
  return [...points.values()];
}
