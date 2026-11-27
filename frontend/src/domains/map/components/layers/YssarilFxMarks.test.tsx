import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import { KeyholeMark, YssarilFxDefs, frondPath, keyholePath } from "./YssarilFxMarks";

function tile(position: string, x: number, y: number): Tile {
  return { position, systemId: "47", planets: {}, unitsByFaction: {}, properties: { x, y } } as unknown as Tile;
}

describe("Yssaril Guild of Spies marks (RULES.md 62.22)", () => {
  it("a rival home: shadow fronds, the keyhole with its key, the blade, the card and 3 shards", () => {
    const { container } = render(
      <svg>
        <YssarilFxDefs />
        <KeyholeMark tile={tile("104", 300, 120)} index={1} />
      </svg>,
    );
    const mark = container.querySelector("[data-mark='keyhole']");
    expect(mark).not.toBeNull();
    expect(mark?.getAttribute("transform")).toContain("translate(");
    expect(mark?.querySelectorAll("[data-card]")).toHaveLength(1);
    expect(mark?.querySelectorAll("[data-shard]")).toHaveLength(3);
    expect(mark?.querySelectorAll("path").length).toBeGreaterThanOrEqual(9 + 1 + 3); // fronds+lock+shards
    expect(container.querySelector("#fxSpyBlade")).not.toBeNull();
  });

  it("glyphs: a closed keyhole outline and a pointed frond", () => {
    expect(keyholePath(20)).toMatch(/^M .* A 20 20 0 1 1 .* Z$/);
    expect(frondPath(100)).toBe("M 0 0 Q 16 45 0 100 Q -16 45 0 0 Z");
  });
});
