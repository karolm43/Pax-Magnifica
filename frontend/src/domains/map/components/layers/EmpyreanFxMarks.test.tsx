import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import { VoidEyeMark, VoidTetherMark, borderSeam } from "./EmpyreanFxMarks";

function tile(position: string, x: number, y: number): Tile {
  return { position, systemId: "47", planets: {}, unitsByFaction: {}, properties: { x, y } } as unknown as Tile;
}

describe("Empyrean board effects (RULES.md 62.20)", () => {
  it("border seam: midpoint of the two systems, drawn across the line joining them", () => {
    const seam = borderSeam({ x: 0, y: 0 }, { x: 0, y: 300 });
    expect(seam.mid).toEqual({ x: 0, y: 150 });
    expect(seam.normal).toEqual({ x: 0, y: 1 });
    expect(Math.abs(seam.along.x)).toBe(1);
    expect(Math.abs(seam.along.y)).toBe(0);
    expect(Math.abs(seam.angle) % 180).toBe(0); // horizontal seam between stacked hexes
  });

  it("void eye: the frontier token drops in everywhere, the eye opens only where it explores", () => {
    const { container } = render(
      <svg>
        <VoidEyeMark tile={tile("201", 0, 0)} index={0} explore={false} />
        <VoidEyeMark tile={tile("202", 400, 0)} index={1} explore />
      </svg>,
    );
    const images = [...container.querySelectorAll("image")].map((i) => i.getAttribute("href") ?? "");
    expect(images).toHaveLength(2);
    expect(images.every((href) => href.includes("token_frontier"))).toBe(true);
    const explored = container.querySelectorAll("[data-explore]");
    expect(explored).toHaveLength(1);
    expect(explored[0].querySelectorAll("ellipse")).toHaveLength(1); // the pupil
  });

  it("void tether: the token on the seam; the old border dissolves without it", () => {
    const { container } = render(
      <svg>
        <VoidTetherMark a={tile("104", 0, 0)} b={tile("105", 0, 300)} />
        <VoidTetherMark a={tile("101", 0, 600)} b={tile("102", 0, 900)} closing />
      </svg>,
    );
    const groups = container.querySelectorAll("svg > g");
    expect(groups).toHaveLength(2);
    expect(groups[1].hasAttribute("data-closing")).toBe(true);
    expect(groups[0].querySelector("image")?.getAttribute("href")).toContain("void_tether");
    expect(groups[0].querySelectorAll("ellipse")).toHaveLength(5); // the chain links
  });
});
