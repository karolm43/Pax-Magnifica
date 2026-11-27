import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Tile } from "@/entities/game/types";
import { useWormholeHoverStore } from "../../wormholeLinks";
import { WormholeLinkLayer } from "./WormholeLinkLayer";

const creuss = { color: "blue", faction: "ghost", wormholeLinks: { "102": ["104"] } };
const sol = { color: "red", faction: "sol" };
let desk: typeof creuss | typeof sol = creuss;

vi.mock("@/domains/game-shell/components/TurnControls/useDeskPlayer", () => ({
  useDeskPlayer: () => desk,
}));

const tile = (position: string, systemId: string, x: number) =>
  ({ position, systemId, tokens: [], properties: { x, y: 0 } }) as unknown as Tile;

function ownLinks() {
  const { container } = render(
    <WormholeLinkLayer
      tiles={[tile("102", "40", 0), tile("104", "39", 400)]}
      contentSize={{ width: 800, height: 400 }}
    />,
  );
  return container.querySelectorAll('g[data-kind="ALPHA"]');
}

describe("WormholeLinkLayer: Quantum Entanglement links (RULES.md 61.7)", () => {
  beforeEach(() => {
    useWormholeHoverStore.getState().setHovered({ position: "102", kinds: ["BETA"] });
  });

  it("from a beta draws an alpha destination in the alpha colour, for its owner", () => {
    desk = creuss;
    expect(ownLinks()).toHaveLength(1);
  });

  it("hides them from every other player", () => {
    desk = sol;
    expect(ownLinks()).toHaveLength(0);
  });
});

describe("WormholeLinkLayer: system with several wormholes", () => {
  it("hovering one wormhole shows the connections of all of them", () => {
    desk = sol;
    useWormholeHoverStore.getState().setHovered({ position: "000", kinds: ["ALPHA"] });
    // Wormhole nexus (alpha, beta, gamma) -> one alpha system and one beta system.
    const { container } = render(
      <WormholeLinkLayer
        tiles={[tile("000", "82b", 0), tile("102", "39", 400), tile("104", "40", 800)]}
        contentSize={{ width: 1200, height: 400 }}
      />,
    );
    expect(container.querySelectorAll('g[data-kind="ALPHA"]')).toHaveLength(1);
    expect(container.querySelectorAll('g[data-kind="BETA"]')).toHaveLength(1);
  });
});
