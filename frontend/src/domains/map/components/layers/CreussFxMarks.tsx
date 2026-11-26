/**
 * Ghosts of Creuss on the board (RULES.md 62.19, 64.4):
 * - `SingularityRiftMark` — Riftwalker Meian's Singularity Reactor (`HERO_BOARD_FX.ghosthero`,
 *   7.6 s): both systems tear open into counter-rotating wormhole vortices joined by a tether;
 *   the OLD tiles lift out of the board, fold and fly along the arc to trade places; under the
 *   flash (4.2 s) the swapped board is revealed (the map's tile covers drop) and the vortices
 *   collapse in ripples.
 * - `WormholePortalMark` — a Creuss wormhole token placed / moved (`TOKEN_BOARD_FX`, 2.8 s): a
 *   vortex in the token's colour opens and the token drops into it; the system it left (when
 *   moved) collapses.
 * Fixed pseudo-random layouts (no `Math.random` in render — everybody sees the same effect).
 */
import type { CSSProperties } from "react";
import type { Tile } from "@/entities/game/types";
import { tileOutline } from "@/entities/geometry/tileOutline";
import { getTileById } from "@/entities/lookup/systems";
import { wormholeTokenImage } from "@/entities/lookup/wormholeTokens";
import { assetUrl } from "@/shared/assets/resolveAsset";
import type { ReplacedTile } from "@/domains/game-shell/components/KeyMoments/keyMoments";
import classes from "./CreussFx.module.css";

type Point = { x: number; y: number };

const vars = (v: Record<string, string | number>) => v as CSSProperties;
const seq = <T,>(n: number, f: (i: number) => T): T[] => Array.from({ length: n }, (_, i) => f(i));

/**
 * Centre of the SHAPE shown in the slot (`systemId` = the tile drawn there; spiral tiles such as
 * Crimson / Kwon are 416x386 drawn from the top-left corner - not the 345x299 hex centre).
 */
export function shapeCentre(t: Tile, systemId: string = t.systemId): Point {
  const { center } = tileOutline(systemId);
  return { x: t.properties.x + center.x, y: t.properties.y + center.y };
}

/** Spiral arm of a vortex (log-spiral-like curve from the rim into the core). */
function armPath(r: number, turn: number): string {
  const pts = seq(9, (k) => {
    const f = k / 8;
    const a = turn * f * Math.PI * 1.6;
    const rr = r * (1 - f * 0.92);
    return `${(rr * Math.cos(a)).toFixed(1)} ${(rr * Math.sin(a)).toFixed(1)}`;
  });
  return `M ${pts[0]} ${pts.slice(1).map((p) => `L ${p}`).join(" ")}`;
}

/**
 * The tether between the two systems: a quadratic arc bowed to one side, plus where each old
 * tile flies (half way + bow = apex). Pure — tested.
 */
export function riftArc(a: Point, b: Point): { d: string; apex: Point; dx: number; dy: number } {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const bow = Math.min(260, len * 0.28);
  const nx = -dy / len;
  const ny = dx / len;
  const control = { x: (a.x + b.x) / 2 + nx * bow * 2, y: (a.y + b.y) / 2 + ny * bow * 2 };
  return {
    d: `M ${a.x} ${a.y} Q ${control.x} ${control.y} ${b.x} ${b.y}`,
    apex: { x: (a.x + b.x) / 2 + nx * bow, y: (a.y + b.y) / 2 + ny * bow },
    dx,
    dy,
  };
}

/** Image of a system tile (`/tiles/...`, as `Tile`), or null without data. */
function tileImage(systemId: string | undefined): string | null {
  const path = systemId ? getTileById(systemId)?.imagePath : undefined;
  return path ? assetUrl(`/tiles/${path}`) : null;
}

/** Sparks thrown when the space snaps back. */
const SPARKS = seq(26, (i) => ({
  angle: i * (360 / 26) + ((i * 37) % 11) - 5,
  dist: 140 + ((i * 53) % 190),
  lag: (i * 29) % 240,
}));

function Vortex({ at, dir, index }: { at: Point; dir: 1 | -1; index: number }) {
  return (
    <g transform={`translate(${at.x} ${at.y})`} style={vars({ "--i": index, "--dir": dir })}>
      <circle className={classes.riftHalo} r={190} fill="url(#fxRiftHalo)" />
      <g className={classes.riftVortex}>
        <g className={classes.riftSpin}>
          {/* Rotation on a <g>: the arm itself has a fill-box origin (CSS) and would pivot
              around its own bounding box, scattering the arms off the vortex centre. */}
          {seq(5, (k) => (
            <g key={k} transform={`rotate(${k * 72})`}>
              <path className={classes.riftArm} d={armPath(150, dir)} style={vars({ "--k": k })} />
            </g>
          ))}
        </g>
        <circle className={classes.riftCore} r={46} fill="url(#fxRiftCore)" />
        <circle className={classes.riftEdge} r={52} />
      </g>
      {[0, 1, 2].map((k) => (
        <circle key={k} className={classes.riftRipple} r={120} style={vars({ "--k": k })} />
      ))}
      {SPARKS.map((s, k) => (
        <g key={k} style={{ rotate: `${s.angle}deg` }}>
          <circle
            className={classes.riftSpark}
            r={2.6}
            style={vars({ "--dist": `${-s.dist}px`, "--lag": `${s.lag}ms` })}
          />
        </g>
      ))}
    </g>
  );
}

/** One old tile lifting out of its slot, folding and flying along the arc to the other slot. */
function FlyingTile({
  from,
  to,
  apex,
  systemId,
  dir,
}: {
  from: Point;
  to: Point;
  apex: Point;
  /** The tile that flies (the one the slot showed before the swap). */
  systemId: string;
  dir: 1 | -1;
}) {
  const image = tileImage(systemId);
  const outline = tileOutline(systemId);
  // Tile-local origin of the art, so that the SHAPE centre sits on the flight point.
  const at = `translate(${-outline.center.x} ${-outline.center.y})`;
  const style = vars({
    "--mx": `${apex.x - from.x}px`,
    "--my": `${apex.y - from.y}px`,
    "--tx": `${to.x - from.x}px`,
    "--ty": `${to.y - from.y}px`,
    "--dir": dir,
  });
  return (
    <g transform={`translate(${from.x} ${from.y})`}>
      <g className={classes.riftFlight} style={style}>
        <g transform={at}>
          {image ? (
            <image href={image} width={outline.width} height={outline.height} />
          ) : (
            <path d={outline.path} className={classes.riftGhostHex} />
          )}
          <path d={outline.path} className={classes.riftGhostRim} />
        </g>
      </g>
    </g>
  );
}

/** Gradients of the rift (tone from `--tone` of the layer). */
export function CreussFxDefs() {
  const c = (color: string, opacity = 1) => ({ stopColor: color, stopOpacity: opacity });
  const tone = (a: number) => c("rgb(var(--tone))", a);
  return (
    <defs>
      <radialGradient id="fxRiftCore">
        <stop offset="0%" style={c("rgb(2 4 14)")} />
        <stop offset="62%" style={c("rgb(8 12 40)")} />
        <stop offset="86%" style={tone(0.9)} />
        <stop offset="100%" style={c("#fff", 0)} />
      </radialGradient>
      <radialGradient id="fxRiftHalo">
        <stop offset="0%" style={tone(0.55)} />
        <stop offset="45%" style={c("rgb(120 80 255)", 0.28)} />
        <stop offset="100%" style={tone(0)} />
      </radialGradient>
      {/* The empty slot = the wormhole's lit mouth (tone + violet), never a black hole. */}
      <radialGradient id="fxRiftVoid">
        <stop offset="0%" style={tone(0.95)} />
        <stop offset="35%" style={c("rgb(120 80 255)", 0.7)} />
        <stop offset="75%" style={c("rgb(40 50 140)", 0.6)} />
        <stop offset="100%" style={tone(0.85)} />
      </radialGradient>
      <linearGradient id="fxRiftTether" gradientUnits="objectBoundingBox">
        <stop offset="0%" style={tone(0.2)} />
        <stop offset="50%" style={c("#fff", 0.95)} />
        <stop offset="100%" style={tone(0.2)} />
      </linearGradient>
    </defs>
  );
}

/**
 * Singularity Reactor — the two swapped systems (`targets`, in any order) and the tiles they
 * held before the swap (`replaced`: position -> old tile id).
 */
export function SingularityRiftMark({ targets, replaced }: { targets: Tile[]; replaced: ReplacedTile[] }) {
  if (targets.length < 2) return null;
  const [first, second] = targets;
  // Until the reveal the map still shows the OLD tile in each slot (`covers`): every shape,
  // centre and flight here follows the old tiles, not the swapped state.
  const oldTile = (t: Tile) => replaced.find((r) => r.position === t.position)?.from ?? t.systemId;
  const a = shapeCentre(first, oldTile(first));
  const b = shapeCentre(second, oldTile(second));
  const arc = riftArc(a, b);
  const back = riftArc(b, a);
  return (
    <g className={classes.rift}>
      {/* While its tile is away, the slot glows as the wormhole's mouth (not a black hole). */}
      {[first, second].map((t, i) => {
        const path = tileOutline(oldTile(t)).path;
        return (
          <g key={`void-${t.position}`} transform={`translate(${t.properties.x} ${t.properties.y})`} style={vars({ "--i": i })}>
            <path className={classes.riftVoid} d={path} fill="url(#fxRiftVoid)" />
            <path className={classes.riftRim} d={path} />
          </g>
        );
      })}
      {/* The tether: glow, bright core, two particle streams running opposite ways. */}
      <path className={classes.riftTetherGlow} d={arc.d} pathLength={1} />
      <path className={classes.riftTether} d={arc.d} pathLength={1} />
      <path className={classes.riftStream} d={arc.d} pathLength={100} />
      <path className={classes.riftStream} data-back d={back.d} pathLength={100} />
      <Vortex at={a} dir={1} index={0} />
      <Vortex at={b} dir={-1} index={1} />
      {/* Each tile lands where ITS shape will be drawn in the other slot (a spiral tile and a
          hex have different centres in the same slot). */}
      <FlyingTile from={a} to={shapeCentre(second, oldTile(first))} apex={arc.apex} systemId={oldTile(first)} dir={1} />
      <FlyingTile from={b} to={shapeCentre(first, oldTile(second))} apex={back.apex} systemId={oldTile(second)} dir={-1} />
    </g>
  );
}

/** Creuss wormhole token: a vortex opens (`closing` = the system the token left collapses). */
export function WormholePortalMark({ tile, token, closing }: { tile: Tile; token: string; closing?: boolean }) {
  const at = shapeCentre(tile);
  const image = closing ? null : wormholeTokenImage(token);
  return (
    <g className={classes.portal} data-closing={closing || undefined} transform={`translate(${at.x} ${at.y})`}>
      <circle className={classes.portalHalo} r={150} fill="url(#fxRiftHalo)" />
      <g className={classes.portalVortex}>
        <g className={classes.riftSpin} style={vars({ "--dir": closing ? -1 : 1 })}>
          {seq(4, (k) => (
            <g key={k} transform={`rotate(${k * 90})`}>
              <path className={classes.portalArm} d={armPath(105, 1)} />
            </g>
          ))}
        </g>
        <circle className={classes.portalCore} r={30} fill="url(#fxRiftCore)" />
      </g>
      {[0, 1].map((k) => (
        <circle key={k} className={classes.portalRing} r={80} style={vars({ "--k": k })} />
      ))}
      {image && (
        <image className={classes.portalToken} href={assetUrl(image)} x={-38} y={-38} width={76} height={76} />
      )}
    </g>
  );
}
