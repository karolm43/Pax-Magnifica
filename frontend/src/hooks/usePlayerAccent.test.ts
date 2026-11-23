import { describe, expect, it } from "vitest";
import { mutedAccentRgb } from "./usePlayerAccent";

const sat = ({ red, green, blue }: { red: number; green: number; blue: number }) => {
  const max = Math.max(red, green, blue) / 255;
  const min = Math.min(red, green, blue) / 255;
  const l = (max + min) / 2;
  return max === min ? 0 : (max - min) / (1 - Math.abs(2 * l - 1));
};

describe("mutedAccentRgb", () => {
  it("czysta czerwień zostaje czerwona, ale przygaszona", () => {
    const m = mutedAccentRgb({ red: 255, green: 0, blue: 0 });
    expect(m.red).toBeGreaterThan(m.green);
    expect(m.green).toBe(m.blue);
    expect(sat(m)).toBeLessThanOrEqual(0.51);
  });

  it("czarny gracz dostaje jasny grafit (widoczny na ciemnym tle)", () => {
    const m = mutedAccentRgb({ red: 0, green: 0, blue: 0 });
    expect(m.red).toBe(m.green);
    expect(m.red).toBeGreaterThanOrEqual(127);
  });

  it("biały nie świeci pełną bielą", () => {
    expect(mutedAccentRgb({ red: 255, green: 255, blue: 255 }).red).toBeLessThan(180);
  });
});
