import type { Point } from "@/entities/data/types";

/**
 * Multi-hop flight paths for the map replay (physical ship movement).
 *
 * A path is the ship's start point plus ordered legs. A `lane` leg flies to its point; a
 * `jump` leg crosses a wormhole: the ship shrinks into a swirl at the entry point and emerges
 * at the leg's point. Consecutive lane legs form one smooth chain (Catmull-Rom through the
 * waypoints) with launch/braking easing at the chain ends only, so a ship cruises through the
 * systems it passes. Anomalies change the pace: leaving a gravity rift slingshots the ship
 * (faster, glowing trail), entering a nebula damps it (slower, dimmed).
 *
 * Everything here is pure: the replay planner uses it for timing and effects, the flight
 * hook for keyframes, so what is drawn always matches the replay duration.
 */

export type FlightLegKind = "lane" | "jump";
export type FlightAnomaly = "rift" | "nebula";

export type FlightLeg = Point & {
  kind: FlightLegKind;
  /** Anomaly of the system this leg ENDS in (where the ship arrives or passes through). */
  anomaly?: FlightAnomaly;
};

export type FlightEffectKind =
  | "wormholeIn"
  | "wormholeOut"
  | "riftWarp"
  | "nebulaDamp";

/** A board effect along the path, timed relative to the flight start. */
export type FlightEffect = Point & {
  kind: FlightEffectKind;
  atMs: number;
  durationMs: number;
};

export const NATIVE_NORTHWEST_ANGLE = -135;
/** Wormhole crossing: shrink into the swirl, a beat of nothing, emerge. */
export const JUMP_MS = 1500;
const JUMP_SHRINK = 0.42;
const JUMP_HIDDEN = 0.16;
const RIFT_SPEED = 1.55;
const NEBULA_SPEED = 0.62;
const EFFECT_MS: Record<FlightEffectKind, number> = {
  wormholeIn: 1100,
  wormholeOut: 1100,
  riftWarp: 1100,
  nebulaDamp: 1500,
};
const DENSE_SAMPLES_PER_LEG = 24;
const KEYFRAME_EVERY_MS = 45;

/** Legacy single-arc duration (history replays without a route). */
export function flightDuration(deltaX: number, deltaY: number): number {
  const distance = Math.hypot(deltaX, deltaY);
  return Math.min(1500, Math.max(780, 650 + distance * 0.35));
}

/**
 * Live moves fly slow and heavy (user decision: the first pace was "way too fast"): about
 * 1.4 s per system, a short repositioning hop to a wormhole still takes a beat.
 */
function legBaseMs(distance: number): number {
  return Math.min(2200, Math.max(650, 900 + distance * 1.6));
}

type Chain = {
  kind: "chain";
  points: Point[];
  /** Pace of each leg of the chain (1 = cruise). */
  speeds: number[];
  anomalies: (FlightAnomaly | undefined)[];
  durationMs: number;
};
type Jump = { kind: "jump"; from: Point; to: Point; durationMs: number };
export type FlightSegment = Chain | Jump;

function legSpeed(
  previousAnomaly: FlightAnomaly | undefined,
  anomaly: FlightAnomaly | undefined,
): number {
  let speed = 1;
  if (previousAnomaly === "rift") speed *= RIFT_SPEED;
  if (anomaly === "nebula") speed *= NEBULA_SPEED;
  return speed;
}

/** Splits a path into smooth fly chains and wormhole jumps, each with its duration. */
export function flightSegments(start: Point, legs: FlightLeg[]): FlightSegment[] {
  const segments: FlightSegment[] = [];
  let chain: Chain | undefined;
  let cursor: Point = start;
  let cursorAnomaly: FlightAnomaly | undefined;
  for (const leg of legs) {
    const to = { x: leg.x, y: leg.y };
    if (leg.kind === "jump") {
      chain = undefined;
      segments.push({ kind: "jump", from: cursor, to, durationMs: JUMP_MS });
    } else {
      if (!chain) {
        chain = { kind: "chain", points: [cursor], speeds: [], anomalies: [], durationMs: 0 };
        segments.push(chain);
      }
      const speed = legSpeed(cursorAnomaly, leg.anomaly);
      chain.points.push(to);
      chain.speeds.push(speed);
      chain.anomalies.push(leg.anomaly);
      chain.durationMs += legBaseMs(Math.hypot(to.x - cursor.x, to.y - cursor.y)) / speed;
    }
    cursor = to;
    cursorAnomaly = leg.anomaly;
  }
  for (const segment of segments) segment.durationMs = Math.round(segment.durationMs);
  return segments;
}

export function flightPathDuration(start: Point, legs: FlightLeg[]): number {
  return flightSegments(start, legs).reduce((total, s) => total + s.durationMs, 0);
}

// --- Geometry --------------------------------------------------------------

function catmullRom(p0: Point, p1: Point, p2: Point, p3: Point, t: number): Point {
  const t2 = t * t;
  const t3 = t2 * t;
  const axis = (a: number, b: number, c: number, d: number) =>
    0.5 *
    (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
  return { x: axis(p0.x, p1.x, p2.x, p3.x), y: axis(p0.y, p1.y, p2.y, p3.y) };
}

type DenseSample = Point & { cost: number; leg: number };

/**
 * Dense samples along a chain with cumulative "cost" = distance / pace, so slow legs take
 * longer. A two-point chain bends slightly (like the legacy single-hop arc).
 */
function denseChain(chain: Chain): DenseSample[] {
  const pts = chain.points;
  const samples: DenseSample[] = [{ ...pts[0], cost: 0, leg: 0 }];
  let bendControl: Point | undefined;
  if (pts.length === 2) {
    const [a, b] = pts;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const distance = Math.hypot(dx, dy) || 1;
    const bend = Math.min(120, Math.max(24, distance * 0.14));
    const direction = dx > 0 || (dx === 0 && dy >= 0) ? 1 : -1;
    bendControl = {
      x: a.x + dx * 0.5 + (-dy / distance) * bend * direction,
      y: a.y + dy * 0.5 + (dx / distance) * bend * direction,
    };
  }
  for (let leg = 0; leg < pts.length - 1; leg += 1) {
    const p0 = pts[Math.max(0, leg - 1)];
    const p1 = pts[leg];
    const p2 = pts[leg + 1];
    const p3 = pts[Math.min(pts.length - 1, leg + 2)];
    for (let i = 1; i <= DENSE_SAMPLES_PER_LEG; i += 1) {
      const t = i / DENSE_SAMPLES_PER_LEG;
      const point = bendControl
        ? {
            x: (1 - t) ** 2 * p1.x + 2 * (1 - t) * t * bendControl.x + t * t * p2.x,
            y: (1 - t) ** 2 * p1.y + 2 * (1 - t) * t * bendControl.y + t * t * p2.y,
          }
        : catmullRom(p0, p1, p2, p3, t);
      const previous = samples[samples.length - 1];
      const distance = Math.hypot(point.x - previous.x, point.y - previous.y);
      samples.push({ ...point, cost: previous.cost + distance / chain.speeds[leg], leg });
    }
  }
  return samples;
}

/** Launch / cruise / braking: eases only at the chain ends. */
function easeInOut(u: number): number {
  return u < 0.5 ? 4 * u * u * u : 1 - (-2 * u + 2) ** 3 / 2;
}

function invertEase(target: number): number {
  let low = 0;
  let high = 1;
  for (let i = 0; i < 24; i += 1) {
    const mid = (low + high) / 2;
    if (easeInOut(mid) < target) low = mid;
    else high = mid;
  }
  return (low + high) / 2;
}

function sampleAtCost(dense: DenseSample[], cost: number): { point: Point; index: number } {
  let index = 1;
  while (index < dense.length - 1 && dense[index].cost < cost) index += 1;
  const a = dense[index - 1];
  const b = dense[index];
  const span = b.cost - a.cost;
  const f = span <= 0 ? 1 : Math.min(1, Math.max(0, (cost - a.cost) / span));
  return { point: { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f }, index };
}

function headingAt(dense: DenseSample[], index: number): number {
  const a = dense[Math.max(0, index - 1)];
  const b = dense[Math.min(dense.length - 1, index + 1)];
  return (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI - NATIVE_NORTHWEST_ANGLE;
}

function unwrapAngle(previous: number, next: number): number {
  let unwrapped = next;
  while (unwrapped - previous > 180) unwrapped -= 360;
  while (unwrapped - previous < -180) unwrapped += 360;
  return unwrapped;
}

const smoothstep = (p: number) => p * p * (3 - 2 * p);

// --- Keyframes -------------------------------------------------------------

export type PathKeyframeOptions = {
  start: Point;
  legs: FlightLeg[];
  rotateToTrajectory: boolean;
  startRotationDeg: number;
  parkRotationDeg: number;
  /** Cargo rides inside its carrier: invisible until it lands. */
  hiddenInFlight?: boolean;
};

type Frame = {
  timeMs: number;
  point: Point;
  rotation: number;
  scale: number;
  glow?: FlightAnomaly;
};

const NO_GLOW = "drop-shadow(0px 0px 0px rgba(0, 0, 0, 0))";
const GLOW: Record<FlightAnomaly, string> = {
  rift: "drop-shadow(0px 0px 7px rgba(192, 132, 252, 0.95))",
  nebula: "drop-shadow(0px 0px 5px rgba(148, 163, 184, 0.7))",
};

function chainFrames(
  chain: Chain,
  startMs: number,
  options: PathKeyframeOptions,
  isFirst: boolean,
  isLast: boolean,
  entryRotation: number,
): Frame[] {
  const dense = denseChain(chain);
  const total = dense[dense.length - 1].cost;
  const count = Math.min(60, Math.max(12, Math.round(chain.durationMs / KEYFRAME_EVERY_MS)));
  const frames: Frame[] = [];
  let previousHeading = entryRotation;
  for (let i = 0; i <= count; i += 1) {
    const u = i / count;
    const { point, index } = sampleAtCost(dense, easeInOut(u) * total);
    const raw = unwrapAngle(previousHeading, headingAt(dense, index));
    previousHeading = raw;
    let rotation = 0;
    if (options.rotateToTrajectory) {
      // Bank out of the parked heading at launch, swing to the park heading when landing.
      const depart = isFirst ? smoothstep(Math.min(1, u / 0.18)) : 1;
      rotation = entryRotation + (raw - entryRotation) * depart;
      if (isLast) {
        const land = smoothstep(Math.max(0, Math.min(1, (u - 0.8) / 0.2)));
        rotation += (unwrapAngle(rotation, options.parkRotationDeg) - rotation) * land;
      }
    }
    const leg = dense[index].leg;
    const glow =
      chain.anomalies[leg] === "nebula"
        ? "nebula"
        : leg > 0 && chain.anomalies[leg - 1] === "rift"
          ? "rift"
          : undefined;
    frames.push({ timeMs: startMs + u * chain.durationMs, point, rotation, scale: 1, glow });
  }
  return frames;
}

function jumpFrames(jump: Jump, startMs: number, rotation: number): Frame[] {
  const shrinkEnd = startMs + jump.durationMs * JUMP_SHRINK;
  const emergeStart = shrinkEnd + jump.durationMs * JUMP_HIDDEN;
  const end = startMs + jump.durationMs;
  return [
    { timeMs: startMs, point: jump.from, rotation, scale: 1 },
    { timeMs: shrinkEnd, point: jump.from, rotation: rotation + 300, scale: 0 },
    { timeMs: emergeStart, point: jump.to, rotation: rotation + 300, scale: 0 },
    { timeMs: end, point: jump.to, rotation: rotation + 720, scale: 1 },
  ];
}

/** Keyframes for the whole path plus its total duration (linear timing: pace is baked in). */
export function buildPathKeyframes(options: PathKeyframeOptions): {
  keyframes: Keyframe[];
  durationMs: number;
} {
  const segments = flightSegments(options.start, options.legs);
  const frames: Frame[] = [];
  let clock = 0;
  let rotation = options.startRotationDeg;
  segments.forEach((segment, index) => {
    const isFirst = index === 0;
    const isLast = index === segments.length - 1;
    const produced =
      segment.kind === "chain"
        ? chainFrames(segment, clock, options, isFirst, isLast, rotation)
        : jumpFrames(segment, clock, options.rotateToTrajectory ? rotation : 0);
    // Each segment starts where the previous one ended: drop the duplicated joint frame.
    // Jumps spin whole turns, so the heading stays continuous across them.
    frames.push(...(frames.length > 0 ? produced.slice(1) : produced));
    clock += segment.durationMs;
    rotation = produced[produced.length - 1]?.rotation ?? rotation;
  });
  const durationMs = Math.max(1, clock);
  const keyframes = frames.map((frame, index): Keyframe => {
    const last = index === frames.length - 1;
    return {
      offset: Math.min(1, frame.timeMs / durationMs),
      opacity: options.hiddenInFlight && !last ? 0 : 1,
      filter: frame.glow ? GLOW[frame.glow] : NO_GLOW,
      transform: `translate(-50%, -50%) translate(${frame.point.x}px, ${frame.point.y}px) rotate(${frame.rotation}deg) scale(${frame.scale})`,
    };
  });
  if (keyframes.length > 0) {
    keyframes[0].offset = 0;
    keyframes[keyframes.length - 1].offset = 1;
  }
  return { keyframes, durationMs };
}

// --- Effects ---------------------------------------------------------------

/** Wormhole swirls and anomaly pulses along the path, timed from the flight start. */
export function flightEffects(start: Point, legs: FlightLeg[]): FlightEffect[] {
  const effects: FlightEffect[] = [];
  const push = (kind: FlightEffectKind, point: Point, atMs: number) =>
    effects.push({ kind, x: point.x, y: point.y, atMs: Math.round(atMs), durationMs: EFFECT_MS[kind] });
  let clock = 0;
  for (const segment of flightSegments(start, legs)) {
    if (segment.kind === "jump") {
      push("wormholeIn", segment.from, clock);
      push("wormholeOut", segment.to, clock + segment.durationMs * (JUMP_SHRINK + JUMP_HIDDEN) - 250);
    } else {
      const dense = denseChain(segment);
      const total = dense[dense.length - 1].cost;
      segment.points.slice(1).forEach((point, leg) => {
        const anomaly = segment.anomalies[leg];
        if (!anomaly) return;
        // Time the ship reaches this waypoint: invert the chain easing at its cost.
        const cost = lastSampleOfLeg(dense, leg)?.cost ?? total;
        const atMs = clock + invertEase(total > 0 ? cost / total : 1) * segment.durationMs;
        push(anomaly === "rift" ? "riftWarp" : "nebulaDamp", point, atMs - (anomaly === "nebula" ? 200 : 120));
      });
    }
    clock += segment.durationMs;
  }
  return effects.map((effect) => ({ ...effect, atMs: Math.max(0, effect.atMs) }));
}

function lastSampleOfLeg(dense: DenseSample[], leg: number): DenseSample | undefined {
  for (let i = dense.length - 1; i >= 0; i -= 1) if (dense[i].leg === leg) return dense[i];
  return undefined;
}
