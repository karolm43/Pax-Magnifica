import {
  boostConflicts,
  draftAsLeg,
  flightBatches,
  legRequest,
  movesSeparately,
  needsSeparateOrder,
  replannedLeg,
  neededBoosts,
  planIncoming,
  stagedElsewhere,
  type StagedLeg,
} from "./flightPlan";
import { pickKey, type DraftPick, type MoveRouteData, type MoveRouteShip } from "./routeTypes";

const ship = (over: Partial<MoveRouteShip>): MoveRouteShip => ({
  baseType: "carrier",
  count: 1,
  capacity: 4,
  reachable: true,
  alone: true,
  withShips: [],
  bonusOptions: [],
  bonusMax: 1,
  reason: "",
  ...over,
});

const route = (from: string, ships: MoveRouteShip[]): MoveRouteData => ({
  active: "000",
  route: [from, "000"],
  reason: "",
  alternatives: [],
  waypoints: [],
  ships,
  cargo: [{ position: from, zone: "space", baseType: "infantry", count: 4, capacityUsed: 1 }],
  riftNodes: [],
  riftRolls: true,
  bonuses: [],
});

const pick = (over: Partial<DraftPick>): DraftPick => ({
  kind: "ship",
  position: "101",
  zone: "space",
  baseType: "carrier",
  count: 1,
  max: 1,
  ...over,
});

const leg = (id: string, from: string, picks: DraftPick[], ships: MoveRouteShip[]): StagedLeg => ({
  id,
  from,
  faction: "sol",
  via: [],
  picks: Object.fromEntries(picks.map((p) => [pickKey(p), p])),
  route: route(from, ships),
});

describe("flight plan legs", () => {
  it("a leg sends its ships, cargo and route", () => {
    const l = leg(
      "a",
      "101",
      [pick({}), pick({ kind: "cargo", baseType: "infantry", count: 2, max: 4 })],
      [ship({})],
    );
    expect(legRequest(l)).toEqual({
      faction: "sol",
      fromPosition: "101",
      ships: [{ baseType: "carrier", count: 1 }],
      cargo: [{ baseType: "infantry", count: 2, fromZone: "space", fromPosition: "101" }],
      route: ["101", "000"],
      ionStormToken: null,
      gravityDrive: false,
      tempesta: false,
      imperator: false,
    });
  });

  it("only the leg whose ship needs a one-ship bonus spends it", () => {
    const slow = ship({ baseType: "dreadnought", alone: false, bonusOptions: [["gravity_drive"]] });
    const needs = leg("a", "101", [pick({ baseType: "dreadnought" })], [slow]);
    const plain = leg("b", "102", [pick({ position: "102" })], [ship({})]);
    expect(neededBoosts(needs.route, needs.picks)).toEqual(["gravity_drive"]);
    expect(legRequest(needs).gravityDrive).toBe(true);
    expect(legRequest(plain).gravityDrive).toBe(false);
  });

  it("a Gravleash companion in the leg removes the need for a bonus", () => {
    const follower = ship({
      baseType: "dreadnought",
      alone: false,
      withShips: ["carrier"],
      bonusOptions: [["gravity_drive"]],
    });
    const l = leg("a", "101", [pick({ baseType: "dreadnought" }), pick({})], [follower, ship({})]);
    expect(neededBoosts(l.route, l.picks)).toEqual([]);
  });

  it("two legs needing the same bonus are a conflict", () => {
    const slow = ship({ baseType: "dreadnought", alone: false, bonusOptions: [["gravity_drive"]] });
    const a = leg("a", "101", [pick({ baseType: "dreadnought" })], [slow]);
    const b = leg("b", "102", [pick({ position: "102", baseType: "dreadnought" })], [slow]);
    expect(boostConflicts([a, b])).toEqual([{ boost: "gravity_drive", froms: ["101", "102"] }]);
    expect(boostConflicts([a])).toEqual([]);
  });

  it("units staged in other legs are not available again", () => {
    const cargo = pick({ kind: "cargo", position: "201", baseType: "infantry", count: 2, max: 4 });
    const a = leg("a", "101", [pick({}), cargo], [ship({})]);
    const target = { kind: "cargo" as const, position: "201", zone: "space", baseType: "infantry" };
    expect(stagedElsewhere([a], undefined, target)).toBe(2);
    expect(stagedElsewhere([a], "a", target)).toBe(0); // editing that very leg
  });

  it("the combined preview counts ships, fighters, ground forces and capacity", () => {
    const a = leg(
      "a",
      "101",
      [
        pick({ count: 2, max: 2 }),
        pick({ kind: "cargo", baseType: "infantry", count: 3, max: 4 }),
        pick({ kind: "cargo", baseType: "fighter", count: 2, max: 2 }),
      ],
      [ship({ count: 2 })],
    );
    const b = leg("b", "102", [pick({ position: "102", baseType: "cruiser" })], [
      ship({ baseType: "cruiser", capacity: 0 }),
    ]);
    const incoming = planIncoming([a, b]);
    expect(incoming.nonFighterShips).toBe(3);
    expect(incoming.fighters).toBe(2);
    expect(incoming.groundForces).toBe(3);
    expect(incoming.capacity).toBe(8);
  });

  it("an open draft becomes a leg only with a route and something picked", () => {
    const draft = { from: "101", faction: "sol", via: [], picks: {}, route: route("101", []) };
    expect(draftAsLeg(draft, "x")).toBeNull();
    const withPick = { ...draft, picks: { [pickKey(pick({}))]: pick({}) } };
    expect(draftAsLeg(withPick, "x")?.from).toBe("101");
    expect(draftAsLeg({ ...withPick, route: null }, "x")).toBeNull();
  });
});

describe("Hil Colish: may move before or after your other ships (RULES.md 62.19)", () => {
  const flagship = leg(
    "fs",
    "103",
    [pick({ position: "103", baseType: "flagship" })],
    [ship({ baseType: "flagship", movesSeparately: true })],
  );
  const carrier = leg("cv", "101", [pick({})], [ship({})]);
  // The flagship's system also holds a carrier; only the carrier is picked.
  const carrierBeside = leg(
    "cv2",
    "103",
    [pick({ position: "103" })],
    [ship({}), ship({ baseType: "flagship", movesSeparately: true })],
  );

  it("only a leg that flies the flagship moves separately", () => {
    expect(movesSeparately(flagship)).toBe(true);
    expect(movesSeparately(carrier)).toBe(false);
    expect(movesSeparately(carrierBeside)).toBe(false);
  });

  it("the choice is asked only with the flagship AND other legs in the plan", () => {
    expect(needsSeparateOrder([flagship])).toBe(false);
    expect(needsSeparateOrder([carrier])).toBe(false);
    expect(needsSeparateOrder([flagship, carrier])).toBe(true);
  });

  it("before = the flagship flies first on its own; after = one flight, flagship last", () => {
    const ids = (batches: StagedLeg[][]) => batches.map((b) => b.map((l) => l.id));
    expect(ids(flightBatches([flagship, carrier], "before"))).toEqual([["fs"], ["cv"]]);
    expect(ids(flightBatches([flagship, carrier], "after"))).toEqual([["cv", "fs"]]);
    expect(ids(flightBatches([flagship], "before"))).toEqual([["fs"]]);
    expect(flightBatches([], "after")).toEqual([]);
  });
});

describe("re-planning a leg after Hil Colish flew first", () => {
  const carrier = leg("cv", "101", [pick({}), pick({ kind: "cargo", baseType: "infantry", count: 2 })], [ship({})]);
  const fresh = (over: Partial<MoveRouteData>): MoveRouteData => ({ ...route("101", [ship({})]), ...over });

  it("takes the route on the CURRENT board (e.g. through the delta in the flagship's new system)", () => {
    const now = fresh({ route: ["101", "103", "000"] });
    const result = replannedLeg(carrier, now);
    expect(typeof result).not.toBe("string");
    expect((result as StagedLeg).route.route).toEqual(["101", "103", "000"]);
    expect(legRequest(result as StagedLeg).route).toEqual(["101", "103", "000"]);
  });

  it("says why it cannot fly any more: no route, ship out of range, cargo off the route", () => {
    expect(replannedLeg(carrier, fresh({ route: null, reason: "Range too short" }))).toMatch(
      /can no longer reach the active system: Range too short/,
    );
    expect(
      replannedLeg(carrier, fresh({ ships: [ship({ reachable: false, reason: "too far" })] })),
    ).toMatch(/carrier can no longer reach.*too far/);
    const away = leg("cv", "101", [pick({}), pick({ kind: "cargo", position: "105", baseType: "infantry" })], [ship({})]);
    expect(replannedLeg(away, fresh({ route: ["101", "000"] }))).toMatch(/no longer passes 105/);
  });
});

