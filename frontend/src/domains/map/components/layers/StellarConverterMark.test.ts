import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import {
  RELIC_BOARD_FX,
  fxTargets,
  useHeroFx,
  veiledPlanetsForQueue,
} from "@/domains/game-shell/components/KeyMoments/heroBoardFx";
import { converterSources } from "./StellarConverterMark";

/** Tile at board coords with optional placed ships (`[id, faction]`) and destroyed planets. */
function tile(position: string, x: number, y: number, ships: [string, string][] = [], destroyed: string[] = []): Tile {
  return {
    position,
    systemId: "26",
    planets: {},
    unitsByFaction: {},
    destroyedPlanets: destroyed,
    properties: { x, y },
    entityPlacements: ships.map(([entityId, faction]) => ({ entityId, entityType: "unit", faction, count: 1, x: 100, y: 50 })),
  } as unknown as Tile;
}

describe("Stellar Converter board effect", () => {
  it("target = system holding the destroyed planet", () => {
    const board = [tile("101", 0, 0), tile("102", 260, 150, [], ["lodor"])];
    const owner = { faction: "sol", color: "blue", planets: ["lodor"] };
    expect(fxTargets(RELIC_BOARD_FX.stellarconverter, board, owner, null)).toEqual(["102"]);
  });

  it("beams start at the player's war sun / dreadnought in ADJACENT systems", () => {
    const target = tile("102", 260, 150, [["dn", "sol"]], ["lodor"]);
    const board = [
      target,
      tile("101", 0, 0, [["dn", "sol"]]), // adjacent
      tile("103", 520, 0, [["ws", "hacan"]]), // adjacent, someone else's
      tile("201", 1040, 600, [["ws", "sol"]]), // far away
    ];
    expect(converterSources(board, target, ["sol", "blue"], { x: 300, y: 200 })).toEqual([{ x: 100, y: 50 }]);
  });

  it("no adjacent firing ship: nearest one on the board, else a beam from above", () => {
    const target = tile("102", 260, 150, [], ["lodor"]);
    const far = tile("301", 1040, 900, [["ws", "sol"]]);
    expect(converterSources([target, far], target, ["sol"], { x: 300, y: 200 })).toEqual([{ x: 1140, y: 950 }]);
    expect(converterSources([target], target, ["sol"], { x: 300, y: 200 })).toEqual([{ x: 180, y: -700 }]);
  });

  it("destroyed planet token stays veiled while its moment is queued", () => {
    expect(
      veiledPlanetsForQueue([{ kind: "hero" }, { kind: "converter", planet: "lodor" }]),
    ).toEqual({ lodor: true });
    useHeroFx.getState().setVeiledPlanets({ lodor: true });
    useHeroFx.getState().unveilPlanet("lodor");
    expect(useHeroFx.getState().veiledPlanets).toEqual({});
  });
});
