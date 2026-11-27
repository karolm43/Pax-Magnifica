/**
 * The Mahact on the board (RULES.md 62.23, 64.4) — Airo Shir Aur: Benediction
 * (`HERO_BOARD_FX.mahacthero`, 7.2 s), between the ORIGIN system (area `benediction_origin`) and
 * the COMBAT system (area `benediction`):
 * - over the origin a crimson gene-sigil unfolds: two counter-rotating rune rings and a double
 *   helix that twists tighter and tighter (the sorcerers seize the fleet);
 * - a golden chain of command whips from the origin to the combat system; glowing motes (the
 *   seized ships) are dragged along it;
 * - with the board flash (3.4 s) six chain links slam shut in a ring around the combat system and
 *   lock (neither side may retreat), the Mahact crown flares above them, a shockwave rolls out;
 * - the chains glow on, then everything fades by 7 s.
 * Fixed pseudo-random layouts (no `Math.random` in render — everybody sees the same effect).
 */
import type { CSSProperties } from "react";
import type { Tile } from "@/entities/game/types";
import { shapeCentre } from "./CreussFxMarks";
import classes from "./MahactFx.module.css";

const vars = (v: Record<string, string | number>) => v as CSSProperties;
const seq = <T,>(n: number, f: (i: number) => T): T[] => Array.from({ length: n }, (_, i) => f(i));

/** Runes on the two sigil rings (angle). */
const RUNES = seq(12, (i) => i * 30);
/** Motes dragged along the chain (delay, size). */
const MOTES = seq(7, (i) => ({ lag: i * 140, r: 5 + ((i * 3) % 4) }));
/** Links of the binding ring around the combat system. */
export const BINDING_LINKS = 6;

/** A double helix (two sine strands) of `len` along the y axis, `amp` wide, `turns` twists. */
export function helixPaths(len: number, amp: number, turns: number): [string, string] {
  const steps = 24;
  const strand = (phase: number) =>
    seq(steps + 1, (k) => {
      const t = k / steps;
      const x = amp * Math.sin(t * turns * Math.PI * 2 + phase);
      const y = -len / 2 + t * len;
      return `${k ? "L" : "M"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(" ");
  return [strand(0), strand(Math.PI)];
}

/** The chain from (0, 0) to (dx, dy): a sagging quadratic curve (the whip). */
export function chainPath(dx: number, dy: number): string {
  const mx = dx / 2;
  const my = dy / 2;
  const len = Math.hypot(dx, dy) || 1;
  const sag = Math.min(140, len * 0.28);
  // Control point pushed sideways from the middle (perpendicular to the line).
  const cx = mx - (dy / len) * sag;
  const cy = my + (dx / len) * sag;
  return `M 0 0 Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${dx.toFixed(1)} ${dy.toFixed(1)}`;
}

/** One chain link: a rounded oblong ring `w` long. */
export function linkPath(w: number): string {
  const h = w * 0.42;
  const r = h / 2;
  return [
    `M ${-w / 2 + r} ${-r}`,
    `L ${w / 2 - r} ${-r}`,
    `A ${r} ${r} 0 0 1 ${w / 2 - r} ${r}`,
    `L ${-w / 2 + r} ${r}`,
    `A ${r} ${r} 0 0 1 ${-w / 2 + r} ${-r}`,
    "Z",
  ].join(" ");
}

/** Gradients (tone from `--tone` of the layer). */
export function MahactFxDefs() {
  const c = (color: string, opacity = 1) => ({ stopColor: color, stopOpacity: opacity });
  const tone = (a: number) => c("rgb(var(--tone))", a);
  return (
    <defs>
      <radialGradient id="fxGeneSigil">
        <stop offset="0%" style={c("#fff", 0.9)} />
        <stop offset="30%" style={tone(0.75)} />
        <stop offset="70%" style={c("rgb(120 10 30)", 0.35)} />
        <stop offset="100%" style={c("rgb(60 0 10)", 0)} />
      </radialGradient>
      <linearGradient id="fxCommandChain" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0%" style={c("rgb(220 40 60)", 0.9)} />
        <stop offset="50%" style={c("rgb(255 214 120)", 1)} />
        <stop offset="100%" style={c("rgb(220 40 60)", 0.9)} />
      </linearGradient>
    </defs>
  );
}

/** Benediction: the sigil over `from`, the chain to `to` and the binding ring around `to`. */
export function BenedictionMark({ from, to }: { from: Tile; to: Tile }) {
  const a = shapeCentre(from);
  const b = shapeCentre(to);
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const chain = chainPath(dx, dy);
  const [strandA, strandB] = helixPaths(150, 34, 2.5);
  return (
    <g className={classes.benediction} data-mark="benediction">
      {/* Origin: the gene-sigil seizes the fleet. */}
      <g className={classes.origin} data-origin transform={`translate(${a.x} ${a.y})`}>
        <circle className={classes.sigilGlow} r={150} fill="url(#fxGeneSigil)" />
        <g className={classes.ringOuter}>
          <circle className={classes.ring} r={128} />
          {RUNES.map((angle) => (
            <rect
              key={angle}
              className={classes.rune}
              x={-5}
              y={-136}
              width={10}
              height={16}
              rx={2}
              transform={`rotate(${angle})`}
            />
          ))}
        </g>
        <g className={classes.ringInner}>
          <circle className={classes.ring} r={92} strokeDasharray="14 10" />
        </g>
        <g className={classes.helix}>
          <path className={classes.strand} d={strandA} />
          <path className={classes.strandB} d={strandB} />
        </g>
      </g>
      {/* The chain of command whipping to the combat system, the seized ships dragged along. */}
      <g transform={`translate(${a.x} ${a.y})`}>
        <path className={classes.chain} data-chain d={chain} pathLength={100} stroke="url(#fxCommandChain)" />
        {MOTES.map((m, k) => (
          <circle
            key={k}
            className={classes.mote}
            data-mote
            r={m.r}
            style={vars({ offsetPath: `path("${chain}")`, "--lag": `${m.lag}ms` })}
          />
        ))}
      </g>
      {/* Combat system: the binding ring locks - no retreat. */}
      <g className={classes.target} data-target transform={`translate(${b.x} ${b.y})`}>
        <circle className={classes.shock} r={60} />
        {seq(BINDING_LINKS, (k) => (
          <g key={k} transform={`rotate(${k * (360 / BINDING_LINKS)}) translate(0 -118)`}>
            <path
              className={classes.link}
              data-link
              d={linkPath(78)}
              style={vars({ "--k": k })}
              transform={k % 2 ? "rotate(90)" : undefined}
            />
          </g>
        ))}
        <path
          className={classes.crown}
          data-crown
          d="M -46 18 L -40 -22 L -20 0 L 0 -34 L 20 0 L 40 -22 L 46 18 Z"
        />
      </g>
    </g>
  );
}
