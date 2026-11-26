/**
 * The Empyrean on the board (RULES.md 62.20, 64.4):
 * - `VoidEyeMark` — Conservator Procyon's Multiverse Shift (`HERO_BOARD_FX.empyreanhero`, 7 s):
 *   in every planetless system a frontier sigil condenses out of a violet void mist and the
 *   frontier token drops into it; where the Empyrean have ships (`explore`) an eye of the void
 *   opens above the token, flares with the board flash (3.7 s), gazes into it and closes — the
 *   token is explored (it leaves the map under the eye).
 * - `VoidTetherMark` — a Void Tether placed / moved onto a border (`TETHER_BOARD_FX`, 3.4 s): a
 *   seam of darkness is drawn along the edge the two systems share, void chains lock it and both
 *   sides recoil from it; `closing` = the border the tether left dissolves.
 * Fixed pseudo-random layouts (no `Math.random` in render — everybody sees the same effect).
 */
import type { CSSProperties } from "react";
import type { Tile } from "@/entities/game/types";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { shapeCentre } from "./CreussFxMarks";
import classes from "./EmpyreanFx.module.css";

type Point = { x: number; y: number };

const vars = (v: Record<string, string | number>) => v as CSSProperties;
const seq = <T,>(n: number, f: (i: number) => T): T[] => Array.from({ length: n }, (_, i) => f(i));

/** Frontier token art (`assets/tokens`, as the map draws it). */
export const FRONTIER_TOKEN_IMAGE = "/tokens/token_frontier.png";
/** Length of the drawn seam: one hex side of a map tile (345 px wide flat-top hex). */
const SEAM_LENGTH = 172;

/**
 * The border two edge-neighbour systems share: its midpoint, the seam's direction (unit vector
 * along the edge) and the normal (unit vector from `a` to `b`). Pure — tested.
 */
export function borderSeam(a: Point, b: Point): { mid: Point; along: Point; normal: Point; angle: number } {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const normal = { x: dx / len, y: dy / len };
  const along = { x: -normal.y, y: normal.x };
  return {
    mid: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 },
    along,
    normal,
    angle: (Math.atan2(along.y, along.x) * 180) / Math.PI,
  };
}

/** Motes of the void mist drawn into a sigil (angle, distance, delay). */
const MOTES = seq(18, (i) => ({
  angle: i * 20 + ((i * 41) % 13) - 6,
  dist: 120 + ((i * 59) % 110),
  lag: (i * 37) % 520,
}));
/** Stars inside the sigil (x, y, radius, delay). */
const STARS = seq(9, (i) => ({
  x: Math.round(Math.cos(i * 2.4) * (14 + ((i * 17) % 30))),
  y: Math.round(Math.sin(i * 2.4) * (14 + ((i * 23) % 30))),
  r: 1.6 + (i % 3) * 0.9,
  lag: (i * 113) % 900,
}));
/** Rays of the eye's flare. */
const RAYS = seq(14, (i) => ({ angle: i * (360 / 14) + ((i * 29) % 9) - 4, len: 150 + ((i * 47) % 120) }));
/** Sparks crackling along the tether seam (offset along the seam, side, delay). */
const SEAM_SPARKS = seq(14, (i) => ({
  at: ((i * 37) % 100) / 100 - 0.5,
  side: i % 2 ? 1 : -1,
  dist: 26 + ((i * 31) % 40),
  lag: 900 + ((i * 71) % 900),
}));

/** Gradients and the mist filter (tone from `--tone` of the layer). */
/* Note: no `transform-box: fill-box` on <g> (CSS): a rotated group would pivot around its own
   bounding box; groups here are centred on (0, 0), the default origin. */
export function EmpyreanFxDefs() {
  const c = (color: string, opacity = 1) => ({ stopColor: color, stopOpacity: opacity });
  const tone = (a: number) => c("rgb(var(--tone))", a);
  return (
    <defs>
      <radialGradient id="fxVoidMist">
        <stop offset="0%" style={c("rgb(10 4 26)", 0.85)} />
        <stop offset="45%" style={c("rgb(40 16 90)", 0.55)} />
        <stop offset="78%" style={tone(0.22)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <radialGradient id="fxVoidSigil">
        <stop offset="0%" style={c("rgb(4 2 12)")} />
        <stop offset="70%" style={c("rgb(22 10 52)")} />
        <stop offset="92%" style={tone(0.9)} />
        <stop offset="100%" style={c("#fff", 0)} />
      </radialGradient>
      <radialGradient id="fxVoidIris">
        <stop offset="0%" style={c("#fff")} />
        <stop offset="18%" style={c("rgb(255 236 200)")} />
        <stop offset="40%" style={tone(1)} />
        <stop offset="78%" style={c("rgb(60 20 140)")} />
        <stop offset="100%" style={c("rgb(10 4 30)")} />
      </radialGradient>
      <radialGradient id="fxVoidFlare">
        <stop offset="0%" style={c("#fff", 0.95)} />
        <stop offset="35%" style={tone(0.6)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      <linearGradient id="fxVoidSeam" gradientUnits="objectBoundingBox">
        <stop offset="0%" style={tone(0)} />
        <stop offset="18%" style={tone(0.9)} />
        <stop offset="50%" style={c("#fff", 0.95)} />
        <stop offset="82%" style={tone(0.9)} />
        <stop offset="100%" style={tone(0)} />
      </linearGradient>
      <filter id="fxVoidWisp" x="-60%" y="-60%" width="220%" height="220%">
        <feTurbulence type="fractalNoise" baseFrequency="0.022" numOctaves="3" seed="11" />
        <feDisplacementMap in="SourceGraphic" scale="55" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </defs>
  );
}

/** Almond outline of the eye (upper / lower lid) - width `w`, opening height `h`. */
function lid(w: number, h: number, upper: boolean): string {
  const s = upper ? -1 : 1;
  return `M ${-w} 0 Q 0 ${s * h * 2} ${w} 0 Q 0 ${s * h * 0.6} ${-w} 0 Z`;
}

/** Multiverse Shift in one system: the frontier sigil, and the eye where it explores. */
export function VoidEyeMark({ tile, index, explore }: { tile: Tile; index: number; explore: boolean }) {
  const at = shapeCentre(tile);
  return (
    <g
      className={classes.eye}
      data-explore={explore || undefined}
      transform={`translate(${at.x} ${at.y})`}
      style={vars({ "--i": index % 12 })}
    >
      <g className={classes.mist} filter="url(#fxVoidWisp)">
        <circle r={190} fill="url(#fxVoidMist)" />
        <circle r={130} cx={36} cy={-22} fill="url(#fxVoidMist)" />
      </g>
      {MOTES.map((m, k) => (
        <g key={k} style={{ rotate: `${m.angle}deg` }}>
          <circle
            className={classes.mote}
            r={2.4}
            style={vars({ "--dist": `${-m.dist}px`, "--lag": `${m.lag}ms` })}
          />
        </g>
      ))}
      <g className={classes.sigil}>
        <circle r={64} fill="url(#fxVoidSigil)" />
        <circle className={classes.sigilRim} r={66} />
        <circle className={classes.sigilRune} r={84} pathLength={100} />
        {STARS.map((s, k) => (
          <circle
            key={k}
            className={classes.star}
            cx={s.x}
            cy={s.y}
            r={s.r}
            style={vars({ "--lag": `${s.lag}ms` })}
          />
        ))}
        <image
          className={classes.token}
          href={assetUrl(FRONTIER_TOKEN_IMAGE)}
          x={-36}
          y={-36}
          width={72}
          height={72}
        />
      </g>
      {explore && (
        <g className={classes.gaze}>
          <circle className={classes.flare} r={230} fill="url(#fxVoidFlare)" />
          <g className={classes.rays}>
            {RAYS.map((r, k) => (
              <g key={k} transform={`rotate(${r.angle})`}>
                <rect className={classes.ray} x={-2.5} y={-r.len} width={5} height={r.len - 60} />
              </g>
            ))}
          </g>
          <g className={classes.eyeBody}>
            <path className={classes.lidGlow} d={lid(110, 44, true)} />
            <path className={classes.lidGlow} d={lid(110, 44, false)} />
            <g className={classes.iris}>
              <circle r={40} fill="url(#fxVoidIris)" />
              <ellipse className={classes.pupil} rx={7} ry={30} />
            </g>
            <path className={classes.lidUpper} d={lid(112, 46, true)} />
            <path className={classes.lidLower} d={lid(112, 46, false)} />
          </g>
        </g>
      )}
    </g>
  );
}

/** Void Tether on the border of `a` and `b` (`closing` = the border it left dissolves). */
export function VoidTetherMark({ a, b, closing }: { a: Tile; b: Tile; closing?: boolean }) {
  const seam = borderSeam(shapeCentre(a), shapeCentre(b));
  const half = SEAM_LENGTH / 2;
  return (
    <g
      className={classes.tether}
      data-closing={closing || undefined}
      transform={`translate(${seam.mid.x} ${seam.mid.y}) rotate(${seam.angle})`}
    >
      {/* Both sides recoil from the seam (the systems are no longer adjacent for others). */}
      {[-1, 1].map((side) => (
        <path
          key={side}
          className={classes.recoil}
          d={`M ${-half} ${side * 18} Q 0 ${side * 70} ${half} ${side * 18}`}
          style={vars({ "--side": side })}
        />
      ))}
      <line className={classes.seamGlow} x1={-half} y1={0} x2={half} y2={0} pathLength={1} />
      <line className={classes.seamCore} x1={-half} y1={0} x2={half} y2={0} pathLength={1} />
      <rect className={classes.seamLight} x={-half} y={-3} width={SEAM_LENGTH} height={6} fill="url(#fxVoidSeam)" />
      {seq(5, (k) => (
        <ellipse
          key={k}
          className={classes.link}
          cx={-half * 0.8 + (k * half * 1.6) / 4}
          cy={0}
          rx={15}
          ry={8}
          style={vars({ "--k": k })}
        />
      ))}
      {SEAM_SPARKS.map((s, k) => (
        <circle
          key={k}
          className={classes.spark}
          cx={s.at * SEAM_LENGTH}
          cy={0}
          r={2.2}
          style={vars({ "--dy": `${s.side * s.dist}px`, "--lag": `${s.lag}ms` })}
        />
      ))}
      <image
        className={classes.tetherToken}
        href={assetUrl("/borders/void_tether.png")}
        x={-28}
        y={-28}
        width={56}
        height={56}
      />
    </g>
  );
}
