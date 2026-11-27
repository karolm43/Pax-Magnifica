import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import {
  BINDING_LINKS,
  BenedictionMark,
  MahactFxDefs,
  chainPath,
  helixPaths,
  linkPath,
} from "./MahactFxMarks";

function tile(position: string, x: number, y: number): Tile {
  return { position, systemId: "47", planets: {}, unitsByFaction: {}, properties: { x, y } } as unknown as Tile;
}

describe("Mahact Benediction marks (RULES.md 62.23)", () => {
  it("origin sigil, the chain with its motes and the binding ring at the combat system", () => {
    const { container } = render(
      <svg>
        <MahactFxDefs />
        <BenedictionMark from={tile("102", 0, 0)} to={tile("103", 345, 0)} />
      </svg>,
    );
    const mark = container.querySelector("[data-mark='benediction']");
    expect(mark).not.toBeNull();
    expect(mark?.querySelectorAll("[data-origin]")).toHaveLength(1);
    expect(mark?.querySelectorAll("[data-chain]")).toHaveLength(1);
    expect(mark?.querySelectorAll("[data-mote]").length).toBeGreaterThanOrEqual(5);
    expect(mark?.querySelectorAll("[data-link]")).toHaveLength(BINDING_LINKS);
    expect(mark?.querySelectorAll("[data-crown]")).toHaveLength(1);
    expect(container.querySelector("#fxCommandChain")).not.toBeNull();
  });

  it("glyphs: a chain from the origin to the target, two helix strands, closed links", () => {
    expect(chainPath(300, 0)).toMatch(/^M 0 0 Q 150\.0 .* 300\.0 0\.0$/);
    const [a, b] = helixPaths(100, 20, 2);
    expect(a.startsWith("M ")).toBe(true);
    expect(a).not.toEqual(b);
    expect(linkPath(50)).toMatch(/^M .* Z$/);
  });
});
