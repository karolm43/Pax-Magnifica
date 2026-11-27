/**
 * The Yssaril on the board (RULES.md 62.22, 64.4) — Kyver, Blade and Key: Guild of Spies
 * (`HERO_BOARD_FX.yssarilhero`, 6.8 s), over EVERY rival's home system (area `kyver`):
 * - jungle shadows creep in around the system (fronds closing like a hand over a lamp);
 * - in the dark an eye slit opens and settles into a glowing keyhole; a key slides in and turns;
 * - with the board flash (3.0 s) a blade slashes across the lock and the keyhole splits;
 * - a card silhouette rises out of the cut and drifts towards the spy (the shown card taken),
 *   while three torn shards scatter (or the three random discards) and the shadows withdraw.
 * Fixed pseudo-random layouts (no `Math.random` in render — everybody sees the same effect).
 */
import type { CSSProperties } from "react";
import type { Tile } from "@/entities/game/types";
import { shapeCentre } from "./CreussFxMarks";
import classes from "./YssarilFx.module.css";

const vars = (v: Record<string, string | number>) => v as CSSProperties;
const seq = <T,>(n: number, f: (i: number) => T): T[] => Array.from({ length: n }, (_, i) => f(i));

/** Jungle fronds closing in around the system (angle, length, delay). */
const FRONDS = seq(9, (i) => ({ angle: i * 40 + ((i * 17) % 13), len: 150 + ((i * 37) % 50), lag: (i * 97) % 500 }));
/** Torn card shards scattering after the slash (angle, distance, spin). */
const SHARDS = seq(3, (i) => ({ angle: -150 + i * 60, dist: 120 + i * 18, spin: (i - 1) * 40 + 25 }));

/** The keyhole glyph: a round head over a flared slot, `r` = head radius. */
export function keyholePath(r: number): string {
  const slot = r * 1.9;
  return [
    `M ${-r * 0.42} ${r * 0.55}`,
    `A ${r} ${r} 0 1 1 ${r * 0.42} ${r * 0.55}`,
    `L ${r * 0.75} ${slot}`,
    `L ${-r * 0.75} ${slot}`,
    "Z",
  ].join(" ");
}

/** One frond: a thin curved leaf from the rim inwards, `len` long. */
export function frondPath(len: number): string {
  const w = len * 0.16;
  return `M 0 0 Q ${w} ${len * 0.45} 0 ${len} Q ${-w} ${len * 0.45} 0 0 Z`;
}

/** Gradients (tone from `--tone` of the layer). */
export function YssarilFxDefs() {
  const c = (color: string, opacity = 1) => ({ stopColor: color, stopOpacity: opacity });
  const tone = (a: number) => c("rgb(var(--tone))", a);
  return (
    <defs>
      <radialGradient id="fxSpyShadow">
        <stop offset="0%" style={c("rgb(2 8 4)", 0.15)} />
        <stop offset="55%" style={c("rgb(2 10 5)", 0.7)} />
        <stop offset="100%" style={c("rgb(0 0 0)", 0)} />
      </radialGradient>
      <radialGradient id="fxSpyGlow">
        <stop offset="0%" style={c("#fff", 0.95)} />
        <stop offset="35%" style={tone(0.85)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <linearGradient id="fxSpyBlade" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0%" style={tone(0)} />
        <stop offset="45%" style={c("#fff", 0.95)} />
        <stop offset="55%" style={tone(0.9)} />
        <stop offset="100%" style={tone(0)} />
      </linearGradient>
    </defs>
  );
}

/** Kyver in one rival home system. */
export function KeyholeMark({ tile, index }: { tile: Tile; index: number }) {
  const at = shapeCentre(tile);
  return (
    <g
      className={classes.spy}
      data-mark="keyhole"
      transform={`translate(${at.x} ${at.y})`}
      style={vars({ "--i": index % 12 })}
    >
      <circle className={classes.shadow} r={190} fill="url(#fxSpyShadow)" />
      {FRONDS.map((f, k) => (
        <g key={k} transform={`rotate(${f.angle}) translate(0 ${-190})`}>
          <path className={classes.frond} d={frondPath(f.len * 0.5)} style={vars({ "--lag": `${f.lag}ms` })} />
        </g>
      ))}
      <ellipse className={classes.eye} rx={70} ry={20} />
      <g className={classes.lock}>
        <circle className={classes.glow} r={70} fill="url(#fxSpyGlow)" />
        <path className={classes.keyhole} d={keyholePath(26)} />
        <g className={classes.key}>
          <rect className={classes.keyBit} x={-5} y={-8} width={10} height={58} rx={3} />
          <circle className={classes.keyBow} cy={-24} r={16} />
        </g>
      </g>
      <rect
        className={classes.blade}
        x={-170}
        y={-4}
        width={340}
        height={8}
        rx={4}
        fill="url(#fxSpyBlade)"
        transform="rotate(-32)"
      />
      <rect className={classes.card} data-card x={-26} y={-38} width={52} height={76} rx={6} />
      {SHARDS.map((s, k) => (
        <g key={k} style={{ rotate: `${s.angle}deg` }}>
          <path
            className={classes.shard}
            data-shard
            d="M -10 -14 L 12 -12 L 8 15 L -12 11 Z"
            style={vars({ "--dist": `${s.dist}px`, "--spin": `${s.spin}deg` })}
          />
        </g>
      ))}
    </g>
  );
}
