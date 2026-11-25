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
export const JUMP_MS = 2400;
/**
 * Ignition: the ship lifts off and its engines spool up, without turning. It comes about
 * onto its course while it gains speed and swings to its parked heading while it brakes,
 * so it never pivots in place (user decision: "too much rotation, not flying").
 * Settle: it sets down on the board once stopped.
 */
export const IGNITION_MS = 600;
export const SETTLE_MS = 450;
/** Longest stretch of a flight spent coming about (start) or swinging to park (end). */
const TURN_WINDOW_MS = 1500;
const TURN_WINDOW_SHARE = 0.32;
/** The nose steers toward the path this far ahead (px), so turns lead into corners. */
const LOOK_AHEAD_PX = 70;
/** Lifted off the board in flight: slightly bigger, with a deeper shadow below. */
const LIFT_SCALE = 0.1;
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
 * Live moves fly slow and heavy, like an armada (user decisions: "way too fast", then
 * "a little bit slower", then "I want to see weight"): about 2.8 s per system; a short hop
 * (landing, reaching a wormhole) still takes a beat.
 */
function legBaseMs(distance: number): number {
  return Math.min(4400, Math.max(1300, 1800 + distance * 3.4));
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
  return (
    IGNITION_MS +
    flightSegments(start, legs).reduce((total, s) => total + s.durationMs, 0) +
    SETTLE_MS
  );
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

type DenseSample = Point & { cost: number; dist: number; leg: number };

/**
 * Dense samples along a chain with cumulative "cost" = distance / pace, so slow legs take
 * longer, and cumulative distance `dist` for steering. A single hop is a straight line: the
 * ship holds its heading across the whole flight.
 */
function denseChain(chain: Chain): DenseSample[] {
  const pts = chain.points;
  const samples: DenseSample[] = [{ ...pts[0], cost: 0, dist: 0, leg: 0 }];
  for (let leg = 0; leg < pts.length - 1; leg += 1) {
    const p0 = pts[Math.max(0, leg - 1)];
    const p1 = pts[leg];
    const p2 = pts[leg + 1];
    const p3 = pts[Math.min(pts.length - 1, leg + 2)];
    for (let i = 1; i <= DENSE_SAMPLES_PER_LEG; i += 1) {
      const point = catmullRom(p0, p1, p2, p3, i / DENSE_SAMPLES_PER_LEG);
      const previous = samples[samples.length - 1];
      const distance = Math.hypot(point.x - previous.x, point.y - previous.y);
      samples.push({
        ...point,
        cost: previous.cost + distance / chain.speeds[leg],
        dist: previous.dist + distance,
        leg,
      });
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

function angleOf(from: Point, to: Point): number {
  return (Math.atan2(to.y - from.y, to.x - from.x) * 180) / Math.PI - NATIVE_NORTHWEST_ANGLE;
}

/**
 * Steering heading at `point` (between samples `index - 1` and `index`): toward the path a
 * little ahead, like a helmsman, so the nose turns smoothly into a corner instead of
 * snapping at it. At the very end of the chain it keeps the final tangent.
 */
function headingAt(dense: DenseSample[], index: number, point: Point = dense[index]): number {
  const target = dense[index].dist + LOOK_AHEAD_PX;
  let ahead = index;
  while (ahead < dense.length - 1 && dense[ahead].dist < target) ahead += 1;
  const aim = dense[ahead];
  if (Math.hypot(aim.x - point.x, aim.y - point.y) > 4) return angleOf(point, aim);
  return angleOf(dense[Math.max(0, dense.length - 3)], dense[dense.length - 1]);
}

function unwrapAngle(previous: number, next: number): number {
  let unwrapped = next;
  while (unwrapped - previous > 180) unwrapped -= 360;
  while (unwrapped - previous < -180) unwrapped += 360;
  return unwrapped;
}

const smoothstep = (p: number) => p * p * (3 - 2 * p);
const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

// --- Keyframes -------------------------------------------------------------

export type PathKeyframeOptions = {
  start: Point;
  legs: FlightLeg[];
  rotateToTrajectory: boolean;
  startRotationDeg: number;
  parkRotationDeg: number;
};

type Frame = {
  timeMs: number;
  point: Point;
  rotation: number;
  scale: number;
  /** 0 = resting on the board, 1 = lifted in flight. */
  lift: number;
  glow?: FlightAnomaly;
};

const NO_GLOW = "drop-shadow(0px 0px 0px rgba(0, 0, 0, 0))";

function shadow(lift: number): string {
  const offset = (3 + 15 * lift).toFixed(1);
  const blur = (2 + 9 * lift).toFixed(1);
  const alpha = (0.25 + 0.3 * lift).toFixed(2);
  return `drop-shadow(0px ${offset}px ${blur}px rgba(0, 0, 0, ${alpha}))`;
}
const GLOW: Record<FlightAnomaly, string> = {
  rift: "drop-shadow(0px 0px 7px rgba(192, 132, 252, 0.95))",
  nebula: "drop-shadow(0px 0px 5px rgba(148, 163, 184, 0.7))",
};

type ChainTurns = {
  /** Heading held when the chain starts: the ship comes about from it while launching. */
  from?: number;
  /** Heading it swings to while braking at the chain's end (the parked heading). */
  to?: number;
};

function chainFrames(
  chain: Chain,
  startMs: number,
  options: PathKeyframeOptions,
  entryRotation: number,
  turns: ChainTurns,
): Frame[] {
  const dense = denseChain(chain);
  const total = dense[dense.length - 1].cost;
  const count = Math.min(60, Math.max(12, Math.round(chain.durationMs / KEYFRAME_EVERY_MS)));
  const window = Math.min(TURN_WINDOW_SHARE, TURN_WINDOW_MS / Math.max(1, chain.durationMs));
  const frames: Frame[] = [];
  let previousHeading = entryRotation;
  for (let i = 0; i <= count; i += 1) {
    const u = i / count;
    const { point, index } = sampleAtCost(dense, easeInOut(u) * total);
    const course = unwrapAngle(previousHeading, headingAt(dense, index, point));
    previousHeading = course;
    // Comes about while gaining speed, swings to its parked heading while braking.
    let heading = course;
    if (turns.from !== undefined) {
      const from = unwrapAngle(course, turns.from);
      heading = from + (course - from) * smoothstep(clamp01(u / window));
    }
    if (turns.to !== undefined) {
      const to = unwrapAngle(heading, turns.to);
      heading += (to - heading) * smoothstep(clamp01((u - (1 - window)) / window));
    }
    const rotation = options.rotateToTrajectory ? heading : 0;
    const leg = dense[index].leg;
    const glow =
      chain.anomalies[leg] === "nebula"
        ? "nebula"
        : leg > 0 && chain.anomalies[leg - 1] === "rift"
          ? "rift"
          : undefined;
    frames.push({
      timeMs: startMs + u * chain.durationMs,
      point,
      rotation,
      scale: 1,
      lift: 1,
      glow,
    });
  }
  return frames;
}

/**
 * Wormhole crossing: the ship dives into the swirl holding its heading and shrinks away,
 * then emerges from the linked gate already facing its next course. No spinning.
 */
function jumpFrames(jump: Jump, startMs: number, rotation: number, exitRotation: number): Frame[] {
  const shrinkEnd = startMs + jump.durationMs * JUMP_SHRINK;
  const emergeStart = shrinkEnd + jump.durationMs * JUMP_HIDDEN;
  const end = startMs + jump.durationMs;
  const exit = unwrapAngle(rotation, exitRotation);
  return [
    { timeMs: startMs, point: jump.from, rotation, scale: 1, lift: 1 },
    { timeMs: shrinkEnd, point: jump.from, rotation, scale: 0, lift: 1 },
    { timeMs: emergeStart, point: jump.to, rotation: exit, scale: 0, lift: 1 },
    { timeMs: end, point: jump.to, rotation: exit, scale: 1, lift: 1 },
  ];
}

/** Heading a chain starts on (rotation units). */
function chainStartHeading(segment: FlightSegment | undefined): number | undefined {
  return segment?.kind === "chain" ? headingAt(denseChain(segment), 0) : undefined;
}

/**
 * Keyframes for the whole path plus its total duration (linear timing: pace is baked in):
 * ignition (lift off, engines spool up) -> flight (come about while launching, steer along
 * the route, swing to the parked heading while braking) -> settle (set down).
 *
 * `thrust` animates the flying ship's engine flames on the same timeline: they flare as it
 * launches, burn with its speed, die down as it brakes and go cold once it lands.
 */
export function buildPathKeyframes(options: PathKeyframeOptions): {
  keyframes: Keyframe[];
  thrust: Keyframe[];
  durationMs: number;
} {
  const segments = flightSegments(options.start, options.legs);
  const turn = options.rotateToTrajectory;
  const startRotation = turn ? options.startRotationDeg : 0;
  const park = turn ? options.parkRotationDeg : 0;
  const lastSegment = segments.at(-1);
  const frames: Frame[] = [
    { timeMs: 0, point: options.start, rotation: startRotation, scale: 1, lift: 0 },
    { timeMs: IGNITION_MS, point: options.start, rotation: startRotation, scale: 1, lift: 1 },
  ];
  let clock = IGNITION_MS;
  let rotation = startRotation;
  segments.forEach((segment, index) => {
    const produced =
      segment.kind === "chain"
        ? chainFrames(segment, clock, options, rotation, {
            // Comes about while launching; after a wormhole it already faces its course.
            from: index === 0 ? rotation : undefined,
            to: segment === lastSegment ? park : undefined,
          })
        : jumpFrames(
            segment,
            clock,
            rotation,
            turn ? (chainStartHeading(segments[index + 1]) ?? rotation) : 0,
          );
    // Each segment starts where the previous one ended: drop the duplicated joint frame.
    frames.push(...produced.slice(1));
    clock += segment.durationMs;
    rotation = produced[produced.length - 1]?.rotation ?? rotation;
  });
  const last = frames[frames.length - 1];
  clock += SETTLE_MS;
  frames.push({
    timeMs: clock,
    point: last.point,
    rotation: turn ? unwrapAngle(rotation, park) : 0,
    scale: 1,
    lift: 0,
  });
  const durationMs = Math.max(1, clock);
  const offsetOf = (frame: Frame) => Math.min(1, frame.timeMs / durationMs);
  const keyframes = frames.map((frame): Keyframe => {
    const scale = frame.scale * (1 + LIFT_SCALE * frame.lift);
    return {
      offset: offsetOf(frame),
      opacity: 1,
      filter: `${shadow(frame.lift)} ${frame.glow ? GLOW[frame.glow] : NO_GLOW}`,
      transform: `translate(-50%, -50%) translate(${frame.point.x}px, ${frame.point.y}px) rotate(${frame.rotation}deg) scale(${scale})`,
    };
  });
  const thrust = thrustLevels(frames).map(
    (level, index): Keyframe => ({
      offset: offsetOf(frames[index]),
      opacity: Math.min(1, level * 2.5),
      transform: `scale(${level.toFixed(3)}, ${(0.65 + 0.35 * Math.min(1, level)).toFixed(3)})`,
    }),
  );
  for (const list of [keyframes, thrust]) {
    list[0].offset = 0;
    list[list.length - 1].offset = 1;
  }
  return { keyframes, thrust, durationMs };
}

/**
 * Engine output per frame (0 = cold, ~1 = cruise burn): spooling up during ignition, a
 * flare while the ship accelerates, a burn that follows its speed, fading as it brakes.
 */
function thrustLevels(frames: Frame[]): number[] {
  const speeds = frames.map((frame, index) => {
    const next = frames[Math.min(frames.length - 1, index + 1)];
    const dt = next.timeMs - frame.timeMs;
    // Inside a wormhole the ship is gone: its jump between the gates is no speed.
    return dt > 0 && frame.scale > 0
      ? Math.hypot(next.point.x - frame.point.x, next.point.y - frame.point.y) / dt
      : 0;
  });
  const top = Math.max(...speeds) || 1;
  return frames.map((frame, index) => {
    if (index === 0 || frame.lift === 0) return 0;
    if (frame.timeMs <= IGNITION_MS) return 0.7;
    const speed = speeds[index] / top;
    const accelerating = speeds[index] > speeds[index - 1] * 1.01;
    return 0.35 + 0.8 * speed + (accelerating ? 0.45 * (1 - speed) : 0);
  });
}

// --- Effects ---------------------------------------------------------------

/** Wormhole swirls and anomaly pulses along the path, timed from the flight start. */
export function flightEffects(start: Point, legs: FlightLeg[]): FlightEffect[] {
  const effects: FlightEffect[] = [];
  const push = (kind: FlightEffectKind, point: Point, atMs: number) =>
    effects.push({ kind, x: point.x, y: point.y, atMs: Math.round(atMs), durationMs: EFFECT_MS[kind] });
  let clock = IGNITION_MS;
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

// --- Cargo packed into a carrier -------------------------------------------

/** Fighters / ground forces shrinking into their carrier before it launches. */
export const PACK_MS = 1100;
/** ...and coming back out of it at the destination. */
export const UNPACK_MS = 1300;
/** Inside the hull: shrunk to a speck (and fully transparent). */
const PACKED_SCALE = 0.08;
/** Size on reaching the hatch: they shrink as they near the carrier. */
const APPROACH_SCALE = 0.6;

export type CargoRideTimes = { packMs: number; rideMs: number; unpackMs: number };

export function cargoRideDuration({ packMs, rideMs, unpackMs }: CargoRideTimes): number {
  return packMs + rideMs + unpackMs;
}

const CARGO_STEPS = 16;

function headingTo(from: Point, to: Point): number {
  if (Math.hypot(to.x - from.x, to.y - from.y) < 1) return 0;
  return (Math.atan2(to.y - from.y, to.x - from.x) * 180) / Math.PI - NATIVE_NORTHWEST_ANGLE;
}

const easeOutCubic = (u: number) => 1 - (1 - u) ** 3;

/**
 * Pack -> ride -> unpack with the same physics as the ships, relative to the cargo's own
 * start (0,0). Boarding: (fighters turn toward the carrier,) accelerate, brake into the
 * hangar and only then shrink and vanish. Riding: hidden while the carrier flies. Unpacking:
 * emerge from the carrier's landing point `land`, launch out, brake at `arrival`, (fighters
 * turn back to the parked heading). `rotate` = fighters; ground forces stay upright.
 */
export function buildCargoKeyframes({
  board,
  land,
  arrival,
  rotate = false,
  ...times
}: CargoRideTimes & {
  board: Point;
  land: Point;
  arrival: Point;
  rotate?: boolean;
}): {
  keyframes: Keyframe[];
  durationMs: number;
} {
  const durationMs = Math.max(1, cargoRideDuration(times));
  const keyframes: Keyframe[] = [];
  const push = (ms: number, point: Point, rotation: number, scale: number, opacity: number) =>
    keyframes.push({
      offset: Math.min(1, ms / durationMs),
      opacity,
      transform: `translate(-50%, -50%) translate(${point.x}px, ${point.y}px) rotate(${rotation}deg) scale(${scale})`,
    });
  const lerp = (a: Point, b: Point, f: number): Point => ({
    x: a.x + (b.x - a.x) * f,
    y: a.y + (b.y - a.y) * f,
  });
  const origin = { x: 0, y: 0 };

  // Boarding: (turn,) glide toward the carrier shrinking as they near it, then slip under
  // its hull dwindling to a speck as they fade. Drawn below the ship, they go inside it.
  const packHeading = rotate ? unwrapAngle(0, headingTo(origin, board)) : 0;
  for (let i = 0; i <= CARGO_STEPS; i += 1) {
    const u = i / CARGO_STEPS;
    const turn = smoothstep(clamp01(u / 0.25));
    const travel = easeInOut(clamp01((u - 0.1) / 0.8));
    const dock = smoothstep(clamp01((u - 0.6) / 0.4));
    push(
      u * times.packMs,
      lerp(origin, board, travel),
      packHeading * turn,
      1 - (1 - APPROACH_SCALE) * travel - (APPROACH_SCALE - PACKED_SCALE) * dock,
      1 - dock,
    );
  }
  // Riding inside the carrier: hidden, carried to the landing point.
  push(times.packMs + times.rideMs, land, packHeading, PACKED_SCALE, 0);

  // Unpacking: grow out from under the hull while fading in, fly out and brake, then turn
  // to the parked heading.
  const outHeading = rotate ? unwrapAngle(packHeading, headingTo(land, arrival)) : 0;
  const parked = rotate ? unwrapAngle(outHeading, 0) : 0;
  const unpackStart = times.packMs + times.rideMs;
  for (let i = 1; i <= CARGO_STEPS; i += 1) {
    const u = i / CARGO_STEPS;
    const emerge = smoothstep(clamp01(u / 0.45));
    const travel = easeOutCubic(clamp01(u / 0.8));
    const park = smoothstep(clamp01((u - 0.75) / 0.25));
    push(
      unpackStart + u * times.unpackMs,
      lerp(land, arrival, travel),
      outHeading + (parked - outHeading) * park,
      PACKED_SCALE + (1 - PACKED_SCALE) * emerge,
      emerge,
    );
  }
  keyframes[keyframes.length - 1].offset = 1;
  return { durationMs, keyframes };
}
