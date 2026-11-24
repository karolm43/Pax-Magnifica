import { describe, expect, it } from "vitest";
import {
  JUMP_MS,
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
  it("packs into the carrier, rides hidden and unpacks at the landing", () => {
    const times = { packMs: 800, rideMs: 2000, unpackMs: 1000 };
    const { keyframes, durationMs } = buildCargoKeyframes({
      board: { x: 20, y: 10 },
      land: { x: 300, y: -500 },
      arrival: { x: 330, y: -470 },
      ...times,
    });
    expect(durationMs).toBe(cargoRideDuration(times));
    expect(keyframes.map((k) => k.opacity)).toEqual([1, 0, 0, 1]);
    expect(keyframes.map((k) => k.offset)).toEqual([0, 800 / 3800, 2800 / 3800, 1]);
    expect(String(keyframes[1].transform)).toContain("translate(20px, 10px)");
    expect(String(keyframes[2].transform)).toContain("translate(300px, -500px)");
    expect(String(keyframes[3].transform)).toContain("translate(330px, -470px) scale(1)");
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
