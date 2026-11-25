import type { CSSProperties } from "react";
import type { Tile } from "@/entities/game/types";
import { getPlanetPositionsBySystemId } from "@/entities/lookup/planets";
import { DEFAULT_PLANET_RADIUS } from "@/entities/positioning/constants";
import { TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import { neighborTiles } from "@/domains/game-shell/components/KeyMoments/heroBoardFx";
import classes from "./StellarConverterFx.module.css";

type Point = { x: number; y: number };

/**
 * Ships that fire the converter (visual only — the engine already checked BOMBARDMENT):
 * war sun first, then dreadnought, then flagship. One per adjacent system.
 */
const FIRING_SHIPS = ["ws", "dn", "fs"];

/** Fixed pseudo-random layouts (no `Math.random` in render — everyone sees the same blast). */
const seq = <T,>(n: number, f: (i: number) => T) => Array.from({ length: n }, (_, i) => f(i));
/** Crust shards: angle, flight distance, spin, size, delay. */
const SHARDS = seq(22, (i) => ({
  angle: i * (360 / 22) + ((i * 41) % 11) - 5,
  dist: 170 + ((i * 67) % 230),
  spin: ((i % 2 ? 1 : -1) * (120 + ((i * 53) % 260))),
  size: 7 + ((i * 29) % 12),
  lag: (i * 31) % 180,
}));
/** Cracks spreading over the overloaded planet: angle and jag pattern. */
const CRACKS = seq(9, (i) => ({ angle: i * 40 + ((i * 17) % 13), bend: (i % 2 ? 1 : -1) * (8 + (i % 3) * 5) }));
/** Ash left on the orbit after the planet is gone. */
const ASH = seq(46, (i) => ({
  angle: i * (360 / 46) + ((i * 13) % 7),
  r: 1.4 + (i % 4) * 0.7,
  wobble: ((i * 37) % 26) - 13,
}));
/** Sparks thrown out with the blast. */
const SPARKS = seq(34, (i) => ({
  angle: i * (360 / 34) + ((i * 23) % 9),
  dist: 120 + ((i * 59) % 260),
  lag: (i * 19) % 220,
}));

/** Jagged shard polygon around the origin (size = rough radius). */
function shardPath(size: number, i: number): string {
  const a = size;
  const b = size * (0.45 + (i % 3) * 0.15);
  return `M ${-a} ${-b * 0.4} L ${a * 0.2} ${-b} L ${a} ${b * 0.1} L ${-a * 0.1} ${b} Z`;
}

/** Planet centre (board coordinates); tile centre when the planet has no printed position. */
function planetPoint(tile: Tile, planet: string | undefined): Point {
  const local = planet ? getPlanetPositionsBySystemId(tile.systemId)[planet] : undefined;
  if (local) return { x: tile.properties.x + local.x, y: tile.properties.y + local.y };
  return { x: tile.properties.x + TILE_WIDTH / 2, y: tile.properties.y + TILE_HEIGHT / 2 };
}

/** Where a tile's firing ship sits (board coordinates), or `null` without one. */
function firingShip(tile: Tile, keys: string[]): Point | null {
  for (const id of FIRING_SHIPS) {
    const stack = tile.entityPlacements.find(
      (s) => s.entityType === "unit" && s.entityId === id && !s.planetName && keys.includes(s.faction),
    );
    if (stack) return { x: tile.properties.x + stack.x, y: tile.properties.y + stack.y };
  }
  return null;
}

/**
 * Sources of the beams: the player's war suns / dreadnoughts / flagships in systems adjacent
 * to the target; without any (e.g. adjacency through a wormhole) the nearest such ship on the
 * board; without even that, a beam from high above the planet.
 */
export function converterSources(tiles: Tile[], target: Tile, keys: string[], at: Point): Point[] {
  const near = neighborTiles(tiles, target)
    .map((t) => firingShip(t, keys))
    .filter((p): p is Point => p !== null);
  if (near.length > 0) return near;
  const anywhere = tiles
    .filter((t) => t.position !== target.position)
    .map((t) => firingShip(t, keys))
    .filter((p): p is Point => p !== null)
    .sort((p, q) => Math.hypot(p.x - at.x, p.y - at.y) - Math.hypot(q.x - at.x, q.y - at.y));
  return anywhere.length > 0 ? anywhere.slice(0, 1) : [{ x: at.x - 120, y: at.y - 900 }];
}

/**
 * Stellar Converter (8,2 s, moments match `RELIC_BOARD_FX.stellarconverter`):
 * 0–1,4 s the firing ships charge (cold glow, rings collapsing into the hull);
 * 1,4–3,4 s beams lance into the planet, a lattice field envelops it and squeezes it
 * ("concentrated"), the crust overheats and cracks; 3,4 s flash, the planet bursts into
 * tumbling shards, a flat debris ring and a shock wave ("scattered"); the destroyed planet
 * token is revealed under the flash; then a slowly fading belt of ash on the old orbit.
 */
export function StellarConverterMark({
  tiles,
  tile,
  planet,
  ownerKeys,
}: {
  tiles: Tile[];
  tile: Tile;
  planet: string | undefined;
  ownerKeys: string[];
}) {
  const at = planetPoint(tile, planet);
  const sources = converterSources(tiles, tile, ownerKeys, at);
  const R = DEFAULT_PLANET_RADIUS;
  return (
    <g className={classes.converter}>
      {sources.map((s, i) => (
        <g key={`src-${i}`} style={{ "--i": i } as CSSProperties}>
          {/* Charge on the firing ship. */}
          <g transform={`translate(${s.x} ${s.y})`}>
            <circle className={classes.charge} r={46} fill="url(#fxConvCharge)" />
            {[0, 1, 2].map((k) => (
              <circle key={k} className={classes.chargeRing} r={70} style={{ "--k": k } as CSSProperties} />
            ))}
          </g>
          {/* The beam: wide glow, cold core, white filament. */}
          <line className={classes.beamGlow} x1={s.x} y1={s.y} x2={at.x} y2={at.y} pathLength={1} />
          <line className={classes.beamCore} x1={s.x} y1={s.y} x2={at.x} y2={at.y} pathLength={1} />
          <line className={classes.beamFilament} x1={s.x} y1={s.y} x2={at.x} y2={at.y} pathLength={1} />
        </g>
      ))}
      <g transform={`translate(${at.x} ${at.y})`}>
        {/* Ash belt on the old orbit (under everything, after the blast). */}
        <g className={classes.ashBelt}>
          {ASH.map((a, i) => (
            <g key={i} style={{ rotate: `${a.angle}deg` }}>
              <circle className={classes.ash} r={a.r} cx={R * 1.5 + a.wobble} cy={0} />
            </g>
          ))}
        </g>
        {/* Overloaded crust: heat glow and spreading cracks. */}
        <circle className={classes.heat} r={R * 0.95} fill="url(#fxConvHeat)" />
        <g className={classes.cracks}>
          {CRACKS.map((c, i) => (
            <path
              key={i}
              className={classes.crack}
              pathLength={1}
              transform={`rotate(${c.angle})`}
              d={`M 0 0 L ${R * 0.3} ${c.bend} L ${R * 0.6} ${-c.bend * 0.6} L ${R * 0.92} ${c.bend * 0.4}`}
            />
          ))}
        </g>
        {/* Containment lattice enveloping the planet, then squeezing it. */}
        <g className={classes.lattice}>
          <circle className={classes.latticeLine} r={R * 1.25} />
          <ellipse className={classes.latticeLine} rx={R * 1.25} ry={R * 0.42} />
          <ellipse className={classes.latticeLine} rx={R * 1.25} ry={R * 0.42} transform="rotate(60)" />
          <ellipse className={classes.latticeLine} rx={R * 1.25} ry={R * 0.42} transform="rotate(120)" />
          <ellipse className={classes.latticeLine} rx={R * 0.42} ry={R * 1.25} />
        </g>
        <circle className={classes.core} r={R * 0.55} fill="url(#fxConvCore)" />
        {/* The burst. */}
        <circle className={classes.flash} r={R * 4.4} fill="url(#fxConvFlash)" />
        <ellipse className={classes.ring} rx={R * 1.2} ry={R * 0.38} />
        <ellipse className={classes.ring} data-late rx={R * 1.2} ry={R * 0.38} />
        <circle className={classes.shock} r={R} />
        {SHARDS.map((s, i) => (
          <g key={i} style={{ rotate: `${s.angle}deg` }}>
            <path
              className={classes.shard}
              d={shardPath(s.size, i)}
              style={
                {
                  "--dist": `${s.dist}px`,
                  "--spin": `${s.spin}deg`,
                  "--lag": `${s.lag}ms`,
                } as CSSProperties
              }
            />
          </g>
        ))}
        {SPARKS.map((s, i) => (
          <g key={i} style={{ rotate: `${s.angle}deg` }}>
            <circle
              className={classes.spark}
              r={2.2}
              style={{ "--dist": `${s.dist}px`, "--lag": `${s.lag}ms` } as CSSProperties}
            />
          </g>
        ))}
      </g>
    </g>
  );
}

/** Gradients of the converter effect (tone from the layer's `--tone`). */
export function StellarConverterDefs() {
  const c = (color: string, opacity = 1) => ({ stopColor: color, stopOpacity: opacity });
  const tone = (a: number) => c("rgb(var(--tone))", a);
  return (
    <defs>
      <radialGradient id="fxConvCharge">
        <stop offset="0%" style={c("#fff")} />
        <stop offset="30%" style={tone(0.9)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxConvHeat">
        <stop offset="0%" style={c("rgb(255 250 230)", 0.95)} />
        <stop offset="35%" style={c("rgb(255 170 80)", 0.75)} />
        <stop offset="75%" style={c("rgb(200 50 30)", 0.55)} />
        <stop offset="100%" style={c("rgb(90 10 20)", 0)} />
      </radialGradient>
      <radialGradient id="fxConvCore">
        <stop offset="0%" style={c("#fff")} />
        <stop offset="45%" style={c("rgb(210 240 255)", 0.9)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxConvFlash">
        <stop offset="0%" style={c("#fff")} />
        <stop offset="22%" style={c("rgb(225 245 255)", 0.95)} />
        <stop offset="55%" style={tone(0.55)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
    </defs>
  );
}
