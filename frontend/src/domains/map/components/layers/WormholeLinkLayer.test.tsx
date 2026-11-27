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

const tile = (position: string, x: number) =>
  ({ position, systemId: "18", tokens: [], properties: { x, y: 0 } }) as unknown as Tile;

function ownLinks() {
  const { container } = render(
    <WormholeLinkLayer
      tiles={[tile("102", 0), tile("104", 400)]}
      contentSize={{ width: 800, height: 400 }}
    />,
  );
  return container.querySelectorAll('[data-kind="PLAYER"]');
}

describe("WormholeLinkLayer: Quantum Entanglement links (RULES.md 61.7)", () => {
  beforeEach(() => {
    useWormholeHoverStore.getState().setHovered({ position: "102", kinds: [] });
  });

  it("draws them for the player who has them", () => {
    desk = creuss;
    expect(ownLinks()).toHaveLength(1);
  });

  it("hides them from every other player", () => {
    desk = sol;
    expect(ownLinks()).toHaveLength(0);
  });
});
