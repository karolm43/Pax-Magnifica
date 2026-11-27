import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import { TimeWarpMark, hourglassPath } from "./NomadFxMarks";

function tile(position: string, x: number, y: number): Tile {
  return { position, systemId: "47", planets: {}, unitsByFaction: {}, properties: { x, y } } as unknown as Tile;
}

describe("Nomad Time Warp marks (RULES.md 62.21)", () => {
  it("flagship system: a chronometer with 60 ticks, two hands and ghost hexes", () => {
    const { container } = render(
      <svg>
        <TimeWarpMark tile={tile("101", 0, 0)} index={0} kind="flagship" />
      </svg>,
    );
    const warp = container.querySelector("[data-kind='flagship']");
    expect(warp).not.toBeNull();
    expect(warp?.querySelectorAll("[data-long]")).toHaveLength(12); // hour marks
    expect(warp?.querySelectorAll("rect").length).toBe(60 + 2); // ticks + hands
  });

  it("command-token system: an hourglass and the chrono-lock that splits open", () => {
    const { container } = render(
      <svg>
        <TimeWarpMark tile={tile("104", 400, 0)} index={1} kind="token" />
      </svg>,
    );
    const warp = container.querySelector("[data-kind='token']");
    expect(warp?.querySelectorAll("[data-lower]")).toHaveLength(1);
    expect(warp?.querySelectorAll("circle").length).toBeGreaterThan(5); // rising sand
  });

  it("hourglass glyph: two bulbs meeting at a narrow waist", () => {
    expect(hourglassPath(30, 50)).toBe("M -30 -50 L 30 -50 L 4 0 L 30 50 L -30 50 L -4 0 Z");
  });
});
