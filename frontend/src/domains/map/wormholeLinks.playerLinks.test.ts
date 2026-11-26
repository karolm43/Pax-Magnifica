import { describe, expect, it } from "vitest";
import { playerLinkTargets } from "./wormholeLinks";

describe("playerLinkTargets (Quantum Entanglement, RULES.md 61.7)", () => {
  const creuss = {
    color: "blue",
    faction: "ghost",
    wormholeLinks: { "102": ["104", "201", "209"] },
  };
  const sol = { color: "red", faction: "sol" };

  it("only the player with the extra adjacency gets links, in their colour", () => {
    expect(playerLinkTargets("102", [creuss, sol], new Set())).toEqual([
      { position: "104", color: "blue", faction: "ghost" },
      { position: "201", color: "blue", faction: "ghost" },
      { position: "209", color: "blue", faction: "ghost" },
    ]);
  });

  it("systems every player reaches through the hovered wormhole are not repeated", () => {
    expect(playerLinkTargets("102", [creuss], new Set(["201"])).map((l) => l.position)).toEqual([
      "104",
      "209",
    ]);
    expect(playerLinkTargets("105", [creuss, sol], new Set())).toEqual([]);
  });
});
