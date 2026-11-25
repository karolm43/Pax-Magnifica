import type { Point } from "@/entities/data/types";

/**
 * Multi-hop flight paths for the map replay (physical ship movement).
 *
 * A path is the ship's start point plus ordered legs. A `lane` leg flies to its point; a
 * `jump` leg crosses a wormhole: the ship shrinks into a swirl at the entry point and emerges
 * at the leg's point. A `portal` leg crosses a Fracture ingress/egress instead: the ship
 * streaks into a tear in space and shoots out of the linked one (unlike a wormhole swirl).
 * Consecutive lane legs form one smooth chain (Catmull-Rom through the waypoints) with
 * launch/braking easing at the chain ends only, so a ship cruises through the systems it
 * passes. Anomalies change the flight: leaving a gravity rift slingshots the ship (faster,
 * glowing), entering a nebula damps it (slower, dimmed), an asteroid field makes it weave
 * between the rocks (slower), a supernova scorches it (hot glow, shaking).
 *
 * Everything here is pure: the replay planner uses it for timing and effects, the flight
 * hook for keyframes, so what is drawn always matches the replay duration.
 */

/**
 * `swallow`: the ship failed its gravity rift roll - the leg's point is the rift's center,
 * where it spirals into a black hole and is gone (always the last leg).
 */
export type FlightLegKind = "lane" | "jump" | "portal" | "swallow";
export type FlightAnomaly = "rift" | "nebula" | "asteroid" | "supernova";

export type FlightLeg = Point & {
  kind: FlightLegKind;
  /** Anomaly of the system this leg ENDS in (where the ship arrives or passes through). */
  anomaly?: FlightAnomaly;
};

export type FlightEffectKind =
  | "wormholeIn"
  | "wormholeOut"
  | "portalIn"
  | "portalOut"
  | "riftWarp"
  | "nebulaDamp"
  | "asteroidDust"
  | "supernovaFlare"
  | "blackHole";

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
/**
 * Fracture ingress/egress: quicker and more violent than a wormhole. The ship accelerates
 * into the tear stretching into a streak, flashes out, and shoots out of the linked tear.
 */
export const PORTAL_MS = 2000;
const PORTAL_DIVE = 0.4;
const PORTAL_EMERGE = 0.55;
/** How far past the tear the streak carries (px), in and out. */
const PORTAL_STREAK_PX = 42;
const RIFT_SPEED = 1.55;
const NEBULA_SPEED = 0.62;
const ASTEROID_SPEED = 0.8;
/** Distance (px, along the path) around an asteroid field / supernova that the ship feels it. */
const HAZARD_REACH_PX = 115;
/** Weaving between asteroids: sideways swing (px), its wavelength (px), nose swing (deg). */
const WEAVE_PX = 9;
const WEAVE_WAVE_PX = 90;
const WEAVE_TURN_DEG = 12;
/** Supernova buffeting (px). */
const SHAKE_PX = 2.4;
const EFFECT_MS: Record<FlightEffectKind, number> = {
  wormholeIn: 1100,
  wormholeOut: 1100,
  portalIn: 1000,
  portalOut: 1000,
  riftWarp: 1100,
  nebulaDamp: 1500,
  asteroidDust: 1600,
  supernovaFlare: 1400,
  blackHole: 3300,
};
/** The effect starts a beat before the ship reaches the system. */
const ANOMALY_EFFECT: Record<FlightAnomaly, { kind: FlightEffectKind; leadMs: number }> = {
  rift: { kind: "riftWarp", leadMs: 120 },
  nebula: { kind: "nebulaDamp", leadMs: 200 },
  asteroid: { kind: "asteroidDust", leadMs: 300 },
  supernova: { kind: "supernovaFlare", leadMs: 250 },
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
type Jump = { kind: "jump"; from: Point; to: Point; durationMs: number; portal: boolean };
type Swallow = { kind: "swallow"; center: Point; durationMs: number };
export type FlightSegment = Chain | Jump | Swallow;

/**
 * Swallowed by a gravity rift: caught at the rift, the ship is dragged into an ever tighter,
 * ever faster spiral, stretched thin (spaghettified) and shrunk to nothing at its center.
 */
export const SWALLOW_MS = 2400;
const SWALLOW_TURNS = 1.6;
const SWALLOW_STEPS = 32;

function legSpeed(
  previousAnomaly: FlightAnomaly | undefined,
  anomaly: FlightAnomaly | undefined,
): number {
  let speed = 1;
  if (previousAnomaly === "rift") speed *= RIFT_SPEED;
  if (anomaly === "nebula") speed *= NEBULA_SPEED;
  if (anomaly === "asteroid") speed *= ASTEROID_SPEED;
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
    if (leg.kind === "swallow") {
      chain = undefined;
      segments.push({ kind: "swallow", center: to, durationMs: SWALLOW_MS });
    } else if (leg.kind !== "lane") {
      chain = undefined;
      const portal = leg.kind === "portal";
      segments.push({
        kind: "jump",
        from: cursor,
        to,
        durationMs: portal ? PORTAL_MS : JUMP_MS,
        portal,
      });
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
  /** Stretched along the nose (1 = normal): the streak into / out of a Fracture tear. */
  stretch?: number;
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
  asteroid: "drop-shadow(0px 0px 4px rgba(214, 180, 140, 0.65))",
  supernova: "drop-shadow(0px 0px 9px rgba(251, 146, 60, 0.95))",
};

/** Screen direction of a heading in rotation units (the art natively faces north-west). */
function headingVector(rotation: number): Point {
  const radians = ((rotation + NATIVE_NORTHWEST_ANGLE) * Math.PI) / 180;
  return { x: Math.cos(radians), y: Math.sin(radians) };
}

type Hazard = { kind: "asteroid" | "supernova"; dist: number };

/** Asteroid fields and supernovas the chain passes, by distance along it. */
function chainHazards(chain: Chain, dense: DenseSample[]): Hazard[] {
  const hazards: Hazard[] = [];
  chain.anomalies.forEach((anomaly, leg) => {
    if (anomaly !== "asteroid" && anomaly !== "supernova") return;
    const sample = lastSampleOfLeg(dense, leg);
    if (sample) hazards.push({ kind: anomaly, dist: sample.dist });
  });
  return hazards;
}

/**
 * How strongly a hazard acts at `dist` along the chain (0..1): a bell around the system,
 * fading out at the chain ends so launch and landing points stay exact.
 */
function hazardStrength(hazard: Hazard, dist: number, length: number): number {
  const away = Math.abs(dist - hazard.dist);
  if (away >= HAZARD_REACH_PX) return 0;
  const bell = 0.5 * (1 + Math.cos((Math.PI * away) / HAZARD_REACH_PX));
  return bell * clamp01(dist / 50) * clamp01((length - dist) / 50);
}

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
  const hazards = chainHazards(chain, dense);
  const length = dense[dense.length - 1].dist;
  const frames: Frame[] = [];
  let previousHeading = entryRotation;
  for (let i = 0; i <= count; i += 1) {
    const u = i / count;
    const sampled = sampleAtCost(dense, easeInOut(u) * total);
    const { index } = sampled;
    let point = sampled.point;
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
    const leg = dense[index].leg;
    let glow: FlightAnomaly | undefined =
      chain.anomalies[leg] === "nebula"
        ? "nebula"
        : leg > 0 && chain.anomalies[leg - 1] === "rift"
          ? "rift"
          : undefined;
    // Asteroid field: weave between the rocks. Supernova: buffeted by the blast, glowing hot.
    const dist = dense[index].dist;
    const side = headingVector(course + 90);
    for (const hazard of hazards) {
      const strength = hazardStrength(hazard, dist, length);
      if (strength <= 0) continue;
      if (strength > 0.2) glow = hazard.kind;
      if (hazard.kind === "asteroid") {
        const phase = (2 * Math.PI * (dist - hazard.dist)) / WEAVE_WAVE_PX;
        const swing = WEAVE_PX * Math.sin(phase) * strength;
        point = { x: point.x + side.x * swing, y: point.y + side.y * swing };
        heading += WEAVE_TURN_DEG * Math.cos(phase) * strength;
      } else {
        point = {
          x: point.x + SHAKE_PX * Math.sin(i * 2.9) * strength,
          y: point.y + SHAKE_PX * Math.cos(i * 4.3) * strength,
        };
      }
    }
    const rotation = options.rotateToTrajectory ? heading : 0;
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
  const exit = unwrapAngle(rotation, exitRotation);
  if (jump.portal) return portalFrames(jump, startMs, rotation, exit);
  const shrinkEnd = startMs + jump.durationMs * JUMP_SHRINK;
  const emergeStart = shrinkEnd + jump.durationMs * JUMP_HIDDEN;
  const end = startMs + jump.durationMs;
  return [
    { timeMs: startMs, point: jump.from, rotation, scale: 1, lift: 1 },
    { timeMs: shrinkEnd, point: jump.from, rotation, scale: 0, lift: 1 },
    { timeMs: emergeStart, point: jump.to, rotation: exit, scale: 0, lift: 1 },
    { timeMs: end, point: jump.to, rotation: exit, scale: 1, lift: 1 },
  ];
}

/**
 * Fracture ingress -> egress: the ship accelerates into the tear, stretching into a streak,
 * and is gone in a flash past it; it shoots out of the egress tear as a streak, snaps back
 * to its shape and flies on. Faster and harder than a wormhole's slow swirl.
 */
function portalFrames(jump: Jump, startMs: number, rotation: number, exit: number): Frame[] {
  const at = (share: number) => startMs + jump.durationMs * share;
  const ahead = (from: Point, heading: number, px: number): Point => {
    const direction = headingVector(heading);
    return { x: from.x + direction.x * px, y: from.y + direction.y * px };
  };
  const streak = PORTAL_STREAK_PX;
  return [
    { timeMs: startMs, point: jump.from, rotation, scale: 1, lift: 1 },
    {
      timeMs: at(PORTAL_DIVE * 0.75),
      point: ahead(jump.from, rotation, streak * 0.35),
      rotation,
      scale: 1,
      lift: 1,
      stretch: 2.4,
    },
    {
      timeMs: at(PORTAL_DIVE),
      point: ahead(jump.from, rotation, streak),
      rotation,
      scale: 0,
      lift: 1,
      stretch: 4,
    },
    {
      timeMs: at(PORTAL_EMERGE),
      point: ahead(jump.to, exit, -streak),
      rotation: exit,
      scale: 0,
      lift: 1,
      stretch: 4,
    },
    {
      timeMs: at(PORTAL_EMERGE + 0.12),
      point: ahead(jump.to, exit, -streak * 0.35),
      rotation: exit,
      scale: 1,
      lift: 1,
      stretch: 2.4,
    },
    { timeMs: startMs + jump.durationMs, point: jump.to, rotation: exit, scale: 1, lift: 1 },
  ];
}

/** The spiral into the black hole, from where the ship was caught (`from`). */
function swallowFrames(
  swallow: Swallow,
  startMs: number,
  rotation: number,
  from: Point,
  turn: boolean,
): Frame[] {
  const { center } = swallow;
  const radius = Math.hypot(from.x - center.x, from.y - center.y);
  const angle0 = Math.atan2(from.y - center.y, from.x - center.x);
  // Orbit the way the nose already points, so the capture reads as one motion.
  const nose = headingVector(rotation);
  const tangent = { x: -Math.sin(angle0), y: Math.cos(angle0) };
  const direction = nose.x * tangent.x + nose.y * tangent.y >= 0 ? 1 : -1;
  const frames: Frame[] = [{ timeMs: startMs, point: from, rotation, scale: 1, lift: 1 }];
  let heading = rotation;
  for (let step = 1; step <= SWALLOW_STEPS; step += 1) {
    const t = step / SWALLOW_STEPS;
    const pull = t * t;
    const angle = angle0 + direction * SWALLOW_TURNS * 2 * Math.PI * t ** 1.5;
    const point = {
      x: center.x + Math.cos(angle) * radius * (1 - pull),
      y: center.y + Math.sin(angle) * radius * (1 - pull),
    };
    const previous = frames[frames.length - 1].point;
    if (turn && Math.hypot(point.x - previous.x, point.y - previous.y) > 0.5) {
      const motion = unwrapAngle(heading, angleOf(previous, point));
      // The nose is wrenched round onto the spiral over its first part.
      heading += (motion - heading) * smoothstep(clamp01(t / 0.3));
    }
    frames.push({
      timeMs: startMs + t * swallow.durationMs,
      point,
      rotation: turn ? heading : 0,
      scale: 1 - smoothstep(clamp01((t - 0.2) / 0.8)),
      lift: 1,
      glow: "rift",
      stretch: 1 + 2.6 * pull,
    });
  }
  return frames;
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
        : segment.kind === "swallow"
          ? swallowFrames(segment, clock, rotation, frames[frames.length - 1].point, turn)
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
  // Swallowed: nothing is left to set down.
  const gone = lastSegment?.kind === "swallow";
  frames.push({
    timeMs: clock,
    point: last.point,
    rotation: gone ? last.rotation : turn ? unwrapAngle(rotation, park) : 0,
    scale: gone ? 0 : 1,
    lift: 0,
  });
  const durationMs = Math.max(1, clock);
  const offsetOf = (frame: Frame) => Math.min(1, frame.timeMs / durationMs);
  const keyframes = frames.map((frame): Keyframe => {
    const scale = frame.scale * (1 + LIFT_SCALE * frame.lift);
    // The nose axis of the art is its NW diagonal: turn it onto x, stretch, turn back. Every
    // frame carries the same function list, so frames interpolate component-wise.
    const stretch = frame.stretch ?? 1;
    const squeeze = (1 / Math.sqrt(stretch)).toFixed(3);
    return {
      offset: offsetOf(frame),
      opacity: 1,
      filter: `${shadow(frame.lift)} ${frame.glow ? GLOW[frame.glow] : NO_GLOW}`,
      transform: `translate(-50%, -50%) translate(${frame.point.x}px, ${frame.point.y}px) rotate(${frame.rotation}deg) scale(${scale}) rotate(45deg) scale(${stretch}, ${squeeze}) rotate(-45deg)`,
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
    if (segment.kind === "swallow") {
      // The rift opens into a black hole just before the ship is caught.
      push("blackHole", segment.center, clock - 400);
    } else if (segment.kind === "jump" && segment.portal) {
      // The tear opens before the ship reaches it and snaps shut behind it.
      push("portalIn", segment.from, clock);
      push("portalOut", segment.to, clock + segment.durationMs * PORTAL_EMERGE - 300);
    } else if (segment.kind === "jump") {
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
        const { kind, leadMs } = ANOMALY_EFFECT[anomaly];
        push(kind, point, atMs - leadMs);
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
 * `lost` = went down with its carrier in a gravity rift: boards and never comes out.
 */
export function buildCargoKeyframes({
  board,
  land,
  arrival,
  rotate = false,
  lost = false,
  ...times
}: CargoRideTimes & {
  board: Point;
  land: Point;
  arrival: Point;
  rotate?: boolean;
  lost?: boolean;
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
    // Fighters bank toward the carrier as they get under way, not in place.
    const turn = smoothstep(clamp01(u / 0.45));
    const travel = easeInOut(clamp01((u - 0.05) / 0.85));
    const dock = smoothstep(clamp01((u - 0.6) / 0.4));
    push(
      u * times.packMs,
      lerp(origin, board, travel),
      packHeading * turn,
      1 - (1 - APPROACH_SCALE) * travel - (APPROACH_SCALE - PACKED_SCALE) * dock,
      1 - dock,
    );
  }
  // Riding inside the carrier: hidden, carried to the landing point. Fighters turn to their
  // launch heading while still inside, so they come out nose-first instead of spinning out
  // (user decision).
  const outHeading = rotate ? unwrapAngle(packHeading, headingTo(land, arrival)) : 0;
  push(times.packMs + times.rideMs, land, outHeading, PACKED_SCALE, 0);
  if (lost) {
    push(durationMs, land, outHeading, PACKED_SCALE, 0);
    keyframes[keyframes.length - 1].offset = 1;
    return { durationMs, keyframes };
  }

  // Unpacking: launch out of the hull nose-first, growing and fading in, brake, and swing to
  // the parked heading while braking.
  const parked = rotate ? unwrapAngle(outHeading, 0) : 0;
  const unpackStart = times.packMs + times.rideMs;
  for (let i = 1; i <= CARGO_STEPS; i += 1) {
    const u = i / CARGO_STEPS;
    const emerge = smoothstep(clamp01(u / 0.45));
    const travel = easeOutCubic(clamp01(u / 0.85));
    const park = smoothstep(clamp01((u - 0.5) / 0.5));
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
