import { prunePicks, type DraftPick, type MoveRouteData } from "./routeTypes";

const route = (ships: MoveRouteData["ships"], cargo: MoveRouteData["cargo"]): MoveRouteData => ({
  active: "000",
  route: ["301", "201", "101", "000"],
  reason: "",
  alternatives: [],
  waypoints: [],
  ships,
  cargo,
  riftNodes: [],
  bonuses: [],
});

describe("prunePicks - Fighter II", () => {
  it("myśliwiec wybrany jako statek, który sam nie doleci, jedzie jako ładunek", () => {
    const pick: DraftPick = {
      kind: "ship", position: "301", zone: "space", baseType: "fighter", count: 6, max: 6,
    };
    const next = prunePicks(
      { "ship|301|space|fighter": pick },
      route(
        [],
        [{ position: "301", zone: "space", baseType: "fighter", count: 6, capacityUsed: 1 }],
      ),
    );
    expect(Object.values(next)).toEqual([{ ...pick, kind: "cargo" }]);
  });
});
