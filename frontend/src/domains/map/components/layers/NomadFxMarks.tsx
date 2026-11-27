/**
 * The Nomad on the board (RULES.md 62.21, 64.4) — Ahk-Syl Siven's Probability Matrix: Time Warp
 * (`HERO_BOARD_FX.nomadhero`, 7.2 s):
 * - `TimeWarpMark` with `kind="flagship"` (area `time_warp`, the flagship's system): a chronometer
 *   dial unfolds over the system, its hands spin BACKWARDS faster and faster while ghost hexes of
 *   other probabilities peel away in a spiral; with the board flash (3.6 s) the dial bursts into a
 *   time ripple and a faint halo keeps turning (the card lies near the board for the round).
 * - `kind="token"` (area `time_warp_token`, a system with a Nomad command token): an hourglass
 *   whose sand runs UP appears over the token, then the chrono-lock ring around it splits open
 *   after the flash — the flagship may leave that system.
 * Fixed pseudo-random layouts (no `Math.random` in render — everybody sees the same effect).
 */
import type { CSSProperties } from "react";
import type { Tile } from "@/entities/game/types";
import { HEX_PATH, TILE_HEIGHT, TILE_WIDTH } from "@/entities/geometry/tilePositioning";
import { shapeCentre } from "./CreussFxMarks";
import classes from "./NomadFx.module.css";

const vars = (v: Record<string, string | number>) => v as CSSProperties;
const seq = <T,>(n: number, f: (i: number) => T): T[] => Array.from({ length: n }, (_, i) => f(i));

/** Dial ticks: 60 minute marks, every 5th a long hour mark. */
const TICKS = seq(60, (i) => ({ angle: i * 6, long: i % 5 === 0 }));
/** Ghost hexes of other probabilities peeling away (angle, distance, rotation, delay). */
const ECHOES = seq(6, (i) => ({
  angle: i * 60 + 18,
  dist: 70 + i * 26,
  turn: (i % 2 ? 1 : -1) * (14 + i * 6),
  lag: 500 + i * 230,
}));
/** Sand grains rising through the hourglass (x offset, delay). */
const GRAINS = seq(10, (i) => ({ x: ((i * 7) % 9) - 4, lag: (i * 173) % 1400 }));

/** The glyph of one hourglass (upper and lower bulb), `h` = half height. */
export function hourglassPath(w: number, h: number): string {
  return `M ${-w} ${-h} L ${w} ${-h} L 4 0 L ${w} ${h} L ${-w} ${h} L -4 0 Z`;
}

/** Gradients and the shimmer filter (tone from `--tone` of the layer). */
export function NomadFxDefs() {
  const c = (color: string, opacity = 1) => ({ stopColor: color, stopOpacity: opacity });
  const tone = (a: number) => c("rgb(var(--tone))", a);
  return (
    <defs>
      <radialGradient id="fxTimeDial">
        <stop offset="0%" style={c("rgb(4 10 24)", 0.9)} />
        <stop offset="62%" style={c("rgb(10 30 60)", 0.75)} />
        <stop offset="90%" style={tone(0.55)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxTimeRipple">
        <stop offset="0%" style={tone(0)} />
        <stop offset="70%" style={tone(0)} />
        <stop offset="86%" style={c("#fff", 0.9)} />
        <stop offset="94%" style={tone(0.7)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxTimeCore">
        <stop offset="0%" style={c("#fff")} />
        <stop offset="40%" style={tone(0.9)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <filter id="fxTimeShimmer" x="-40%" y="-40%" width="180%" height="180%">
        <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="5" />
        <feDisplacementMap in="SourceGraphic" scale="14" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </defs>
  );
}

/** The chronometer over the flagship's system. */
function FlagshipWarp() {
  return (
    <>
      {ECHOES.map((e, k) => (
        <g key={k} style={{ rotate: `${e.angle}deg` }}>
          {/* The animated group pivots on the system's centre; the hex is centred inside it. */}
          <g
            className={classes.echo}
            style={vars({ "--dist": `${e.dist}px`, "--turn": `${e.turn}deg`, "--lag": `${e.lag}ms` })}
          >
            <path
              className={classes.echoHex}
              d={HEX_PATH}
              transform={`translate(${-TILE_WIDTH / 2} ${-TILE_HEIGHT / 2})`}
            />
          </g>
        </g>
      ))}
      <g className={classes.dial} filter="url(#fxTimeShimmer)">
        <circle r={150} fill="url(#fxTimeDial)" />
        <circle className={classes.dialRim} r={150} />
        <circle className={classes.dialInner} r={112} />
        {TICKS.map((t, k) => (
          <g key={k} transform={`rotate(${t.angle})`}>
            <rect
              className={classes.tick}
              data-long={t.long || undefined}
              x={-1.5}
              y={-146}
              width={3}
              height={t.long ? 22 : 10}
            />
          </g>
        ))}
        <g className={classes.handHour}>
          <rect className={classes.hand} x={-5} y={-74} width={10} height={84} rx={5} />
        </g>
        <g className={classes.handMinute}>
          <rect className={classes.hand} x={-3} y={-128} width={6} height={140} rx={3} />
        </g>
        <circle r={14} fill="url(#fxTimeCore)" />
      </g>
      <circle className={classes.ripple} r={170} fill="url(#fxTimeRipple)" />
      <circle className={classes.ripple} data-late r={170} fill="url(#fxTimeRipple)" />
      <g className={classes.halo}>
        <circle className={classes.haloRing} r={128} pathLength={100} />
      </g>
    </>
  );
}

/** The hourglass and the opening chrono-lock over a system with a Nomad command token. */
function TokenWarp() {
  return (
    <>
      <g className={classes.lock}>
        <path className={classes.lockArc} d="M -96 0 A 96 96 0 0 1 96 0" />
        <path className={classes.lockArc} data-lower d="M 96 0 A 96 96 0 0 1 -96 0" />
      </g>
      <g className={classes.glass}>
        <path className={classes.glassBody} d={hourglassPath(34, 52)} />
        {GRAINS.map((g, k) => (
          <circle
            key={k}
            className={classes.grain}
            cx={g.x}
            cy={40}
            r={2.2}
            style={vars({ "--lag": `${g.lag}ms` })}
          />
        ))}
      </g>
    </>
  );
}

/** Time Warp in one system: the flagship's chronometer or a command token's opened lock. */
export function TimeWarpMark({
  tile,
  index,
  kind,
}: {
  tile: Tile;
  index: number;
  kind: "flagship" | "token";
}) {
  const at = shapeCentre(tile);
  return (
    <g
      className={classes.warp}
      data-kind={kind}
      transform={`translate(${at.x} ${at.y})`}
      style={vars({ "--i": index % 12 })}
    >
      {kind === "flagship" ? <FlagshipWarp /> : <TokenWarp />}
    </g>
  );
}
