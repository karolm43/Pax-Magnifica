/**
 * The Nekro Virus on the board (RULES.md 62.24, 64.4) — UNIT.DSGN.FLAYESH: Polymorphic Algorithm:
 * Devour World (`HERO_BOARD_FX.nekrohero`, 6.6 s) over the DEVOURED planet (area `nekro_devour` +
 * fact `hero_planet`):
 * - a hexagonal viral lattice blinks in around the system, cell by cell (the infection spreads);
 * - six data tendrils crawl from the tile rim onto the planet, a corrupted ring of code segments
 *   spins around it;
 * - with the board flash (3.0 s) the planet implodes: a black core swallows it, shards are torn
 *   outward and sucked back in;
 * - a glowing tech core (the gained technology) rises out of the husk and the Nekro sigil (the
 *   virus triangle with its eye) burns over it, everything fades by 6.4 s.
 * Fixed pseudo-random layouts (no `Math.random` in render — everybody sees the same effect).
 */
import type { CSSProperties } from "react";
import type { Tile } from "@/entities/game/types";
import { getPlanetPositionsBySystemId } from "@/entities/lookup/planets";
import { DEFAULT_PLANET_RADIUS } from "@/entities/positioning/constants";
import { shapeCentre } from "./CreussFxMarks";
import classes from "./NekroFx.module.css";

type Point = { x: number; y: number };

const vars = (v: Record<string, string | number>) => v as CSSProperties;
const seq = <T,>(n: number, f: (i: number) => T): T[] => Array.from({ length: n }, (_, i) => f(i));

/** Lattice cells around the system centre: axial hex ring 1 + ring 2 (q, r). */
export const LATTICE = [
  [0, 0],
  ...[
    [1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1],
    [2, 0], [2, -1], [2, -2], [1, -2], [0, -2], [-1, -1],
    [-2, 0], [-2, 1], [-2, 2], [-1, 2], [0, 2], [1, 1],
  ],
] as [number, number][];
/** Data tendrils crawling onto the planet. */
export const TENDRILS = 6;
/** Shards of the imploding planet (angle, distance, size, delay). */
const SHARDS = seq(18, (i) => ({
  angle: i * 20 + ((i * 37) % 11) - 5,
  dist: 70 + ((i * 53) % 60),
  size: 6 + (i % 4) * 2,
  lag: (i * 23) % 180,
}));
/** Code segments of the corrupted ring (start angle, length in degrees). */
const SEGMENTS = seq(10, (i) => ({ from: i * 36 + ((i * 13) % 9), len: 12 + ((i * 17) % 14) }));

/** A flat-top hexagon of radius `r` centred on (0, 0). */
export function hexPath(r: number): string {
  return (
    seq(6, (k) => {
      const a = (Math.PI / 3) * k;
      return `${k ? "L" : "M"} ${(r * Math.cos(a)).toFixed(1)} ${(r * Math.sin(a)).toFixed(1)}`;
    }).join(" ") + " Z"
  );
}

/** Centre of axial cell (q, r) for flat-top hexes of radius `r`. */
export function cellCentre(q: number, r: number, size: number): Point {
  return { x: size * 1.5 * q, y: size * Math.sqrt(3) * (r + q / 2) };
}

/** A tendril from the rim point at `angle` (deg, distance `reach`) to (0, 0): a wavy cubic. */
export function tendrilPath(angle: number, reach: number, k: number): string {
  const a = (angle * Math.PI) / 180;
  const sx = reach * Math.cos(a);
  const sy = reach * Math.sin(a);
  const bend = (k % 2 ? 1 : -1) * reach * 0.35;
  const nx = -Math.sin(a) * bend;
  const ny = Math.cos(a) * bend;
  const c1 = `${(sx * 0.66 + nx).toFixed(1)} ${(sy * 0.66 + ny).toFixed(1)}`;
  const c2 = `${(sx * 0.33 - nx).toFixed(1)} ${(sy * 0.33 - ny).toFixed(1)}`;
  return `M ${sx.toFixed(1)} ${sy.toFixed(1)} C ${c1} ${c2} 0 0`;
}

/** An arc of the corrupted ring: radius `r`, from `from` deg spanning `len` deg. */
export function arcPath(r: number, from: number, len: number): string {
  const p = (deg: number) => {
    const a = (deg * Math.PI) / 180;
    return `${(r * Math.cos(a)).toFixed(1)} ${(r * Math.sin(a)).toFixed(1)}`;
  };
  return `M ${p(from)} A ${r} ${r} 0 0 1 ${p(from + len)}`;
}

/** Planet centre relative to the system centre (system centre without a printed position). */
export function devourPoint(tile: Tile, planet: string | undefined): Point {
  const centre = shapeCentre(tile);
  const local = planet ? getPlanetPositionsBySystemId(tile.systemId)[planet] : undefined;
  if (!local) return { x: 0, y: 0 };
  return { x: tile.properties.x + local.x - centre.x, y: tile.properties.y + local.y - centre.y };
}

/** Gradients (tone from `--tone` of the layer). */
export function NekroFxDefs() {
  const c = (color: string, opacity = 1) => ({ stopColor: color, stopOpacity: opacity });
  const tone = (a: number) => c("rgb(var(--tone))", a);
  return (
    <defs>
      <radialGradient id="fxNekroInfection">
        <stop offset="0%" style={tone(0.55)} />
        <stop offset="60%" style={c("rgb(90 0 10)", 0.35)} />
        <stop offset="100%" style={c("rgb(20 0 0)", 0)} />
      </radialGradient>
      <radialGradient id="fxNekroVoid">
        <stop offset="0%" style={c("#000", 1)} />
        <stop offset="70%" style={c("rgb(30 0 6)", 0.95)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxNekroCore">
        <stop offset="0%" style={c("#fff", 1)} />
        <stop offset="35%" style={c("rgb(255 160 150)", 0.9)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
    </defs>
  );
}

/** Devour World over `tile`, consuming `planet`. */
export function DevourMark({ tile, planet }: { tile: Tile; planet?: string }) {
  const centre = shapeCentre(tile);
  const at = devourPoint(tile, planet);
  const R = DEFAULT_PLANET_RADIUS;
  const cell = 46;
  const cellHex = hexPath(cell * 0.86);
  return (
    <g className={classes.devour} data-mark="devour" transform={`translate(${centre.x} ${centre.y})`}>
      {/* The infection glow and the viral lattice spreading over the system. */}
      <circle className={classes.infection} r={250} fill="url(#fxNekroInfection)" />
      <g className={classes.lattice}>
        {LATTICE.map(([q, r], k) => {
          const p = cellCentre(q, r, cell);
          return (
            <path
              key={`${q},${r}`}
              className={classes.cell}
              data-cell
              d={cellHex}
              transform={`translate(${p.x.toFixed(1)} ${p.y.toFixed(1)})`}
              style={vars({ "--k": (Math.abs(q) + Math.abs(r) + Math.abs(q + r)) / 2, "--j": k % 5 })}
            />
          );
        })}
      </g>
      <g transform={`translate(${at.x.toFixed(1)} ${at.y.toFixed(1)})`}>
        {/* Data tendrils crawling onto the planet. */}
        {seq(TENDRILS, (k) => (
          <path
            key={k}
            className={classes.tendril}
            data-tendril
            d={tendrilPath(k * (360 / TENDRILS) + 15, 210, k)}
            pathLength={100}
            style={vars({ "--k": k })}
          />
        ))}
        {/* The corrupted ring of code segments. */}
        <g className={classes.ring}>
          {SEGMENTS.map((s, i) => (
            <path key={i} className={classes.segment} d={arcPath(R * 1.55, s.from, s.len)} />
          ))}
        </g>
        {/* The implosion: the black core swallows the planet, shards torn out and sucked in. */}
        <circle className={classes.void} data-void r={R * 1.2} fill="url(#fxNekroVoid)" />
        <g className={classes.shards}>
          {SHARDS.map((s, i) => (
            <g key={i} style={{ rotate: `${s.angle}deg` }}>
              <rect
                className={classes.shard}
                data-shard
                x={-s.size / 2}
                y={-s.size / 2}
                width={s.size}
                height={s.size}
                style={vars({ "--dist": `${s.dist}px`, "--lag": `${s.lag}ms` })}
              />
            </g>
          ))}
        </g>
        <circle className={classes.shock} r={R} />
        {/* The extracted technology core rising out of the husk, the Nekro sigil over it. */}
        <g className={classes.core} data-core>
          <circle r={26} fill="url(#fxNekroCore)" />
          <circle className={classes.coreRing} r={20} />
        </g>
        <g className={classes.sigil} data-sigil>
          <path className={classes.sigilTriangle} d="M 0 -58 L 50 30 L -50 30 Z" />
          <circle className={classes.sigilEye} r={11} cy={6} />
        </g>
      </g>
    </g>
  );
}
