import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import {
  DevourMark,
  LATTICE,
  NekroFxDefs,
  TENDRILS,
  arcPath,
  cellCentre,
  hexPath,
  tendrilPath,
} from "./NekroFxMarks";

function tile(position: string, systemId: string): Tile {
  return { position, systemId, planets: {}, unitsByFaction: {}, properties: { x: 0, y: 0 } } as unknown as Tile;
}

describe("Nekro Devour World marks (RULES.md 62.24)", () => {
  it("lattice, tendrils, the imploding void with shards, the tech core and the sigil", () => {
    const { container } = render(
      <svg>
        <NekroFxDefs />
        <DevourMark tile={tile("105", "19")} planet="wellon" />
      </svg>,
    );
    const mark = container.querySelector("[data-mark='devour']");
    expect(mark).not.toBeNull();
    expect(mark?.querySelectorAll("[data-cell]")).toHaveLength(LATTICE.length);
    expect(mark?.querySelectorAll("[data-tendril]")).toHaveLength(TENDRILS);
    expect(mark?.querySelectorAll("[data-void]")).toHaveLength(1);
    expect(mark?.querySelectorAll("[data-shard]").length).toBeGreaterThanOrEqual(12);
    expect(mark?.querySelectorAll("[data-core]")).toHaveLength(1);
    expect(mark?.querySelectorAll("[data-sigil]")).toHaveLength(1);
    expect(container.querySelector("#fxNekroVoid")).not.toBeNull();
  });

  it("without a known planet the effect centres on the system", () => {
    const { container } = render(
      <svg>
        <DevourMark tile={tile("105", "47")} />
      </svg>,
    );
    expect(container.querySelector("[data-mark='devour']")).not.toBeNull();
  });

  it("glyphs: closed hexes, cell centres, tendrils ending at the planet, ring arcs", () => {
    expect(hexPath(10)).toMatch(/^M 10\.0 0\.0 .* Z$/);
    expect(cellCentre(0, 0, 40)).toEqual({ x: 0, y: 0 });
    expect(cellCentre(1, 0, 40).x).toBeCloseTo(60);
    expect(tendrilPath(0, 200, 0)).toMatch(/^M 200\.0 0\.0 C .* 0 0$/);
    expect(arcPath(50, 0, 90)).toMatch(/^M 50\.0 0\.0 A 50 50 0 0 1/);
  });
});
