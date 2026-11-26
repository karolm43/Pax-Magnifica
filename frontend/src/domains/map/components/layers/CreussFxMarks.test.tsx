import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import { SingularityRiftMark, WormholePortalMark, riftArc, shapeCentre } from "./CreussFxMarks";

function tile(position: string, systemId: string, x: number, y: number): Tile {
  return { position, systemId, planets: {}, unitsByFaction: {}, properties: { x, y } } as unknown as Tile;
}

describe("Creuss board effects (RULES.md 62.19)", () => {
  it("rift arc: from A to B, bowed to one side, apex between the systems", () => {
    const arc = riftArc({ x: 0, y: 0 }, { x: 1000, y: 0 });
    expect(arc.d.startsWith("M 0 0 Q")).toBe(true);
    expect(arc.d.endsWith("1000 0")).toBe(true);
    expect(arc.dx).toBe(1000);
    expect(arc.apex.x).toBe(500);
    expect(Math.abs(arc.apex.y)).toBeGreaterThan(100);
    // The way back bows to the other side, so the two flying tiles do not collide.
    const back = riftArc({ x: 1000, y: 0 }, { x: 0, y: 0 });
    expect(Math.sign(back.apex.y)).toBe(-Math.sign(arc.apex.y));
  });

  it("Singularity Reactor: the OLD tiles fly (images of the tiles before the swap)", () => {
    const targets = [tile("102", "01", 0, 0), tile("105", "26", 900, 300)];
    const { container } = render(
      <svg>
        <SingularityRiftMark
          targets={targets}
          replaced={[
            { position: "102", from: "26" },
            { position: "105", from: "01" },
          ]}
        />
      </svg>,
    );
    const images = [...container.querySelectorAll("image")].map((i) => i.getAttribute("href") ?? "");
    expect(images).toHaveLength(2);
    expect(images[0]).toContain("26"); // Lodor leaves 102 ...
    expect(images[1]).toMatch(/01|jord/i); // ... and Jord leaves 105
  });

  it("Singularity Reactor needs both systems", () => {
    const { container } = render(
      <svg>
        <SingularityRiftMark targets={[tile("102", "01", 0, 0)]} replaced={[]} />
      </svg>,
    );
    expect(container.querySelector("g")).toBeNull();
  });

  it("portal: the token image drops in; the closing vortex has no token", () => {
    const { container } = render(
      <svg>
        <WormholePortalMark tile={tile("205", "19", 0, 0)} token="creussalpha" />
        <WormholePortalMark tile={tile("206", "20", 300, 0)} token="creussalpha" closing />
      </svg>,
    );
    const images = container.querySelectorAll("image");
    expect(images).toHaveLength(1);
    expect(images[0].getAttribute("href")).toContain("token_creussalpha");
    expect(container.querySelector("[data-closing]")).not.toBeNull();
  });

  it("effects centre on the tile SHAPE: hex 345x299, spiral tiles 416x386", () => {
    expect(shapeCentre(tile("102", "26", 100, 200))).toEqual({ x: 272.5, y: 349.5 });
    // Crimson home (spiral art drawn from the top-left corner): centre of the 416x386 shape.
    expect(shapeCentre(tile("102", "118", 100, 200))).toEqual({ x: 308, y: 393 });
    // The slot still shows the OLD tile until the reveal: centre of that tile's shape.
    expect(shapeCentre(tile("102", "26", 0, 0), "118")).toEqual({ x: 208, y: 193 });
  });

  it("vortex arms rotate on a wrapping <g> (a fill-box origin would scatter them)", () => {
    const { container } = render(
      <svg>
        <WormholePortalMark tile={tile("205", "19", 0, 0)} token="creussalpha" />
      </svg>,
    );
    const arms = [...container.querySelectorAll("path")];
    expect(arms.length).toBeGreaterThan(0);
    for (const arm of arms) {
      expect(arm.getAttribute("transform")).toBeNull();
      expect(arm.parentElement?.getAttribute("transform")).toMatch(/^rotate\(/);
    }
  });

  it("Singularity Reactor: a spiral tile flies at its own size and lands on its shape centre", () => {
    const targets = [tile("102", "26", 0, 0), tile("105", "118", 900, 300)];
    const { container } = render(
      <svg>
        <SingularityRiftMark
          targets={targets}
          replaced={[
            { position: "102", from: "118" },
            { position: "105", from: "26" },
          ]}
        />
      </svg>,
    );
    const crimson = [...container.querySelectorAll("image")].find((i) =>
      (i.getAttribute("href") ?? "").includes("118"),
    );
    expect(crimson?.getAttribute("width")).toBe("416");
    expect(crimson?.getAttribute("height")).toBe("386");
  });
});
