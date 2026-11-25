import { describe, expect, it } from "vitest";
import type { PrePlacementTile } from "@/entities/game/types";
import { getPlanetPositionsBySystemId } from "@/entities/lookup/planets";
import { DESTROYED_PLANET_TOKEN, getAllEntityPlacementsForTile } from "./index";

describe("destroyed planet token (Stellar Converter)", () => {
  it("sits on the printed planet's position", () => {
    const tile = {
      systemId: "26",
      tokens: [],
      unitsByFaction: {},
      planets: {},
      commandCounters: [],
      highestProduction: 0,
      destroyedPlanets: ["lodor"],
    } as unknown as PrePlacementTile;
    const token = getAllEntityPlacementsForTile("26", tile).find(
      (p) => p.entityId === DESTROYED_PLANET_TOKEN,
    );
    const at = getPlanetPositionsBySystemId("26").lodor;
    expect(at).toBeDefined();
    expect(token).toMatchObject({ entityType: "token", planetName: "lodor", x: at.x, y: at.y });
  });
});
