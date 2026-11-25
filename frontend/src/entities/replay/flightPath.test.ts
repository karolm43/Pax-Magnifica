import { describe, expect, it } from "vitest";
import {
  IGNITION_MS,
  JUMP_MS,
  SETTLE_MS,
  buildCargoKeyframes,
  buildPathKeyframes,
  cargoRideDuration,
  flightDuration,
  flightEffects,
  flightPathDuration,
  flightSegments,
  type FlightLeg,
} from "./flightPath";

const start = { x: 0, y: 0 };

describe("flightSegments", () => {
  it("flies a live one-system move slower than the legacy arc", () => {
    const legs: FlightLeg[] = [{ x: 300, y: 0, kind: "lane" }];
    expect(flightPathDuration(start, legs)).toBeGreaterThan(
      flightDuration(300, 0),
    );
    expect(flightPathDuration(start, legs)).toBeGreaterThanOrEqual(1300);
  });

  it("joins consecutive lane hops into one smooth chain", () => {
    const legs: FlightLeg[] = [
      { x: 300, y: 0, kind: "lane" },
      { x: 600, y: 100, kind: "lane" },
    ];
    const segments = flightSegments(start, legs);
    expect(segments).toHaveLength(1);
    expect(segments[0].kind).toBe("chain");
  });

  it("splits a wormhole crossing into a fixed-length jump", () => {
    const legs: FlightLeg[] = [
      { x: 100, y: 0, kind: "lane" },
      { x: 900, y: 900, kind: "jump" },
      { x: 950, y: 920, kind: "lane" },
    ];
    const segments = flightSegments(start, legs);
    expect(segments.map((s) => s.kind)).toEqual(["chain", "jump", "chain"]);
    expect(segments[1].durationMs).toBe(JUMP_MS);
  });

  it("speeds up after a gravity rift and slows into a nebula", () => {
    const plain: FlightLeg[] = [
      { x: 300, y: 0, kind: "lane" },
      { x: 600, y: 0, kind: "lane" },
    ];
    const rift: FlightLeg[] = [
      { x: 300, y: 0, kind: "lane", anomaly: "rift" },
      { x: 600, y: 0, kind: "lane" },
    ];
    const nebula: FlightLeg[] = [
      { x: 300, y: 0, kind: "lane" },
      { x: 600, y: 0, kind: "lane", anomaly: "nebula" },
    ];
    expect(flightPathDuration(start, rift)).toBeLessThan(
      flightPathDuration(start, plain),
    );
    expect(flightPathDuration(start, nebula)).toBeGreaterThan(
      flightPathDuration(start, plain),
    );
  });
});

describe("buildPathKeyframes", () => {
  const legs: FlightLeg[] = [
    { x: 100, y: 0, kind: "lane" },
    { x: 900, y: 900, kind: "jump" },
    { x: 950, y: 920, kind: "lane" },
  ];
  const base = {
    start,
    legs,
    rotateToTrajectory: true,
    startRotationDeg: 0,
    parkRotationDeg: 0,
  };

  it("matches the planned duration, with ordered offsets ending at the target", () => {
    const { keyframes, durationMs } = buildPathKeyframes(base);
    expect(durationMs).toBe(flightPathDuration(start, legs));
    const offsets = keyframes.map((k) => k.offset as number);
    expect(offsets[0]).toBe(0);
    expect(offsets.at(-1)).toBe(1);
    expect(offsets).toEqual([...offsets].sort((a, b) => a - b));
    expect(String(keyframes.at(-1)?.transform)).toContain(
      "translate(950px, 920px)",
    );
  });

  const rotationOf = (k: Keyframe) =>
    Number(/rotate\((-?[\d.]+)deg\)/.exec(String(k.transform))?.[1]);

  it("lifts off without pivoting, comes about while moving, and sets down already parked", () => {
    const { keyframes, durationMs } = buildPathKeyframes({
      start,
      legs: [{ x: 0, y: -400, kind: "lane" }],
      rotateToTrajectory: true,
      startRotationDeg: 0,
      parkRotationDeg: 0,
    });
    const [rest, lifted] = keyframes;
    expect(lifted.offset).toBeCloseTo(IGNITION_MS / durationMs, 5);
    // Lifted off the board in place, engines spooling, but not yet turned.
    expect(String(lifted.transform)).toContain("translate(0px, 0px)");
    expect(rotationOf(lifted)).toBe(0);
    expect(String(rest.transform)).toContain("scale(1)");
    expect(String(lifted.transform)).toContain("scale(1.1)");
    // Mid-flight the nose points along the course (due north = 45 deg from the NW art).
    const mid = keyframes[Math.floor(keyframes.length / 2)];
    expect(rotationOf(mid)).toBeCloseTo(45, 0);
    // Settling only sets it down: it swung to its parked heading while braking.
    const [braked, parked] = keyframes.slice(-2);
    expect(parked.offset! - braked.offset!).toBeCloseTo(SETTLE_MS / durationMs, 5);
    expect(rotationOf(braked)).toBeCloseTo(rotationOf(parked), 5);
    expect(String(parked.transform)).toContain("translate(0px, -400px)");
    expect(String(parked.transform)).toContain("scale(1)");
  });

  it("turns gradually: no keyframe step swings the nose by much", () => {
    const { keyframes } = buildPathKeyframes({
      start,
      legs: [
        { x: 300, y: 0, kind: "lane" },
        { x: 450, y: 260, kind: "lane" },
        { x: 750, y: 260, kind: "lane" },
      ],
      rotateToTrajectory: true,
      startRotationDeg: 0,
      parkRotationDeg: 0,
    });
    const rotations = keyframes.map(rotationOf);
    const steps = rotations.slice(1).map((r, i) => Math.abs(r - rotations[i]));
    expect(Math.max(...steps)).toBeLessThan(25);
  });

  it("flies a single hop in a straight line", () => {
    const { keyframes } = buildPathKeyframes({
      start,
      legs: [{ x: 600, y: 0, kind: "lane" }],
      rotateToTrajectory: true,
      startRotationDeg: 0,
      parkRotationDeg: 0,
    });
    for (const k of keyframes) {
      const y = Number(/translate\(-?[\d.e-]+px, (-?[\d.e-]+)px\) rotate/.exec(String(k.transform))?.[1]);
      expect(Math.abs(y)).toBeLessThan(1e-6);
    }
  });

  it("dives into a wormhole without spinning", () => {
    const { keyframes } = buildPathKeyframes(base);
    const rotations = keyframes.map(rotationOf);
    expect(Math.max(...rotations) - Math.min(...rotations)).toBeLessThan(200);
  });

  it("throttles the engines: cold on the board, flaring at launch, cold once landed", () => {
    const { keyframes, thrust } = buildPathKeyframes(base);
    expect(thrust).toHaveLength(keyframes.length);
    expect(thrust.map((k) => k.offset)).toEqual(keyframes.map((k) => k.offset));
    expect(thrust[0].opacity).toBe(0);
    expect(thrust.at(-1)!.opacity).toBe(0);
    const level = (k: Keyframe) => Number(/scale\(([\d.]+),/.exec(String(k.transform))?.[1]);
    expect(Math.max(...thrust.map(level))).toBeGreaterThan(1);
  });

  it("shrinks to nothing inside the wormhole", () => {
    const { keyframes } = buildPathKeyframes(base);
    expect(
      keyframes.some((k) => String(k.transform).endsWith("scale(0)")),
    ).toBe(true);
  });

  it("parks back in the native heading after landing", () => {
    const { keyframes } = buildPathKeyframes({ ...base, parkRotationDeg: 30 });
    const last = String(keyframes.at(-1)?.transform);
    const rotation = Number(/rotate\((-?[\d.]+)deg\)/.exec(last)?.[1]);
    expect(((rotation % 360) + 360) % 360).toBeCloseTo(30, 0);
  });

});

describe("buildCargoKeyframes", () => {
  const times = { packMs: 800, rideMs: 2000, unpackMs: 1000 };
  const ride = (rotate: boolean) =>
    buildCargoKeyframes({
      board: { x: 200, y: 0 },
      land: { x: 300, y: -500 },
      arrival: { x: 330, y: -470 },
      rotate,
      ...times,
    });
  const at = (keyframes: Keyframe[], offset: number) =>
    keyframes.find((k) => Math.abs((k.offset as number) - offset) < 1e-6)!;

  it("boards, rides hidden and unpacks within the planned time", () => {
    const { keyframes, durationMs } = ride(false);
    expect(durationMs).toBe(cargoRideDuration(times));
    const offsets = keyframes.map((k) => k.offset as number);
    expect(offsets).toEqual([...offsets].sort((a, b) => a - b));
    expect(at(keyframes, 0).opacity).toBe(1);
    // Docked inside the carrier, then carried hidden to the landing point.
    expect(at(keyframes, 800 / 3800).opacity).toBe(0);
    expect(String(at(keyframes, 800 / 3800).transform)).toContain("translate(200px, 0px)");
    expect(String(at(keyframes, 2800 / 3800).transform)).toContain("translate(300px, -500px)");
    expect(keyframes.at(-1)).toMatchObject({ offset: 1, opacity: 1 });
    expect(String(keyframes.at(-1)?.transform)).toContain("translate(330px, -470px)");
  });

  it("stays fully visible while travelling and only vanishes when docking", () => {
    const { keyframes } = ride(false);
    const midway = keyframes.filter((k) => (k.offset as number) <= (0.6 * 800) / 3800);
    expect(midway.every((k) => k.opacity === 1)).toBe(true);
  });

  it("turns fighters toward the carrier and back to the parked heading", () => {
    const rotation = (k: Keyframe) =>
      Number(/rotate\((-?[\d.]+)deg\)/.exec(String(k.transform))?.[1]);
    const fighters = ride(true).keyframes;
    expect(rotation(at(fighters, 400 / 3800))).not.toBe(0);
    expect(((rotation(fighters.at(-1)!) % 360) + 360) % 360).toBeCloseTo(0, 5);
    expect(ride(false).keyframes.every((k) => rotation(k) === 0)).toBe(true);
  });
});

describe("fighters leaving a carrier", () => {
  it("emerge already facing out (turned while hidden), never spinning while visible", () => {
    const { keyframes } = buildCargoKeyframes({
      board: { x: 200, y: 0 },
      land: { x: 300, y: -500 },
      arrival: { x: 300, y: -380 },
      rotate: true,
      packMs: 800,
      rideMs: 2000,
      unpackMs: 1000,
    });
    const rotation = (k: Keyframe) =>
      Number(/rotate\((-?[\d.]+)deg\)/.exec(String(k.transform))?.[1]);
    const unpack = keyframes.filter((k) => (k.offset as number) >= 2800 / 3800 - 1e-9);
    // Hidden ride frame already carries the launch heading (due south: 90deg on screen = 225 from the NW art).
    expect(((rotation(unpack[0]) % 360) + 360) % 360).toBeCloseTo(225, 0);
    // While fading in (first visible frames) the heading holds.
    const emerging = unpack.slice(0, 5).map(rotation);
    expect(Math.max(...emerging) - Math.min(...emerging)).toBeLessThan(1);
  });
});

describe("flightEffects", () => {
  it("swirls at both wormhole ends, the exit after the entry", () => {
    const effects = flightEffects(start, [
      { x: 100, y: 0, kind: "lane" },
      { x: 900, y: 900, kind: "jump" },
      { x: 950, y: 920, kind: "lane" },
    ]);
    const into = effects.find((e) => e.kind === "wormholeIn");
    const out = effects.find((e) => e.kind === "wormholeOut");
    expect(into).toMatchObject({ x: 100, y: 0 });
    expect(out).toMatchObject({ x: 900, y: 900 });
    expect(out!.atMs).toBeGreaterThan(into!.atMs);
  });

  it("pulses where the ship passes a gravity rift or enters a nebula", () => {
    const effects = flightEffects(start, [
      { x: 300, y: 0, kind: "lane", anomaly: "rift" },
      { x: 600, y: 0, kind: "lane", anomaly: "nebula" },
    ]);
    expect(effects.map((e) => e.kind)).toEqual(["riftWarp", "nebulaDamp"]);
    expect(effects[1].atMs).toBeGreaterThan(effects[0].atMs);
  });
});
