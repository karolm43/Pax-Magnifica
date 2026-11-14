import {
  otherRoleCount,
  pickKey,
  prunePicks,
  type DraftPick,
  type MoveRouteData,
} from "./routeTypes";

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

describe("Fighter II ze startu: sam albo ładunek", () => {
  const ship = {
    baseType: "fighter", count: 6, capacity: 0, reachable: true, alone: true,
    withShips: [], bonusOptions: [], bonusMax: 1, reason: "",
  };
  const cargo = { position: "301", zone: "space", baseType: "fighter", count: 6, capacityUsed: 1 };

  it("statek i ładunek tych samych sztuk mają wspólny limit", () => {
    const flying: DraftPick = {
      kind: "ship", position: "301", zone: "space", baseType: "fighter", count: 2, max: 6,
    };
    const carried: DraftPick = { ...flying, kind: "cargo", count: 6 };
    const picks = { [pickKey(flying)]: flying, [pickKey(carried)]: carried };
    expect(otherRoleCount(picks, "301", carried)).toBe(2);
    const next = prunePicks(picks, route([ship], [cargo]));
    expect(next[pickKey(flying)].count).toBe(2);
    expect(next[pickKey(carried)].count).toBe(4);
  });

  it("myśliwiec z innego systemu na trasie nie dzieli limitu ze startem", () => {
    const enRoute: DraftPick = {
      kind: "cargo", position: "201", zone: "space", baseType: "fighter", count: 3, max: 3,
    };
    expect(otherRoleCount({ [pickKey(enRoute)]: enRoute }, "301", { ...enRoute, kind: "ship" })).toBe(0);
  });
});
