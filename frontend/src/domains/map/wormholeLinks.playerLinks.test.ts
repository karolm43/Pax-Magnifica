import { describe, expect, it } from "vitest";
import { playerLinkTargets } from "./wormholeLinks";

describe("playerLinkTargets (Quantum Entanglement, RULES.md 61.7)", () => {
  const creuss = { wormholeLinks: { "102": ["104", "201", "209"] } };

  it("only the player with the extra adjacency gets links", () => {
    expect(playerLinkTargets("102", creuss, new Set())).toEqual(["104", "201", "209"]);
    expect(playerLinkTargets("102", {}, new Set())).toEqual([]);
  });

  it("systems every player reaches through the hovered wormhole are not repeated", () => {
    expect(playerLinkTargets("102", creuss, new Set(["201"]))).toEqual([
      "104",
      "209",
    ]);
    expect(playerLinkTargets("105", creuss, new Set())).toEqual([]);
  });
});
