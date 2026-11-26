import {
  asyncOfBase,
  pickKey,
  type DraftPick,
  type MoveDraft,
  type MoveRouteData,
} from "./routeTypes";

/**
 * Flight plan of the Move Ships step (RULES.md 32.4): the player stages one LEG per source
 * system (ships + cargo + route), sees the combined result, then flies everything with one
 * `POST /tactical/move-batch`. Pure helpers - no React, no store.
 */

/** One-ship move bonuses ("+1 move for ONE ship this action"), as named by the route preview. */
export type MoveBoost = "gravity_drive" | "tempesta" | "imperator";

export const BOOST_NAMES: Record<MoveBoost, string> = {
  gravity_drive: "Gravity Drive",
  tempesta: "Ionian Fuel Refinery",
  imperator: "Imperator",
};

const BOOSTS = Object.keys(BOOST_NAMES) as MoveBoost[];

export type StagedLeg = {
  id: string;
  from: string;
  faction: string;
  via: string[];
  picks: Record<string, DraftPick>;
  /** Route preview the leg was staged with (route, ships, cargo along it). */
  route: MoveRouteData;
  /** Ion Storm choice for this leg's route (only when the preview asked for it). */
  ionStormToken?: boolean;
};

/** Leg shape of `POST /tactical/move-batch` (= `MoveShipsRequest`). */
export type MoveLegRequest = {
  faction: string;
  fromPosition: string;
  ships: { baseType: string; count: number }[];
  cargo: { baseType: string; count: number; fromZone: string; fromPosition: string }[];
  route: string[] | null;
  ionStormToken: boolean | null;
  gravityDrive: boolean;
  tempesta: boolean;
  imperator: boolean;
};

const count = (picks: Record<string, DraftPick>, kind: DraftPick["kind"]) =>
  Object.values(picks)
    .filter((p) => p.kind === kind)
    .reduce((n, p) => n + p.count, 0);

export const legShipCount = (picks: Record<string, DraftPick>) => count(picks, "ship");
export const legCargoCount = (picks: Record<string, DraftPick>) => count(picks, "cargo");

/**
 * One-ship bonuses a leg needs: a picked ship that does not reach on its own (and not with a
 * picked Gravleash companion) needs the first bonus combination the route preview offers.
 */
export function neededBoosts(
  route: MoveRouteData,
  picks: Record<string, DraftPick>,
): MoveBoost[] {
  const picked = new Set(
    Object.values(picks)
      .filter((p) => p.kind === "ship" && p.count > 0)
      .map((p) => p.baseType),
  );
  const needed = new Set<MoveBoost>();
  for (const ship of route.ships) {
    if (!picked.has(ship.baseType) || !ship.reachable || ship.alone) continue;
    if (ship.withShips.some((bt) => picked.has(bt))) continue;
    for (const name of ship.bonusOptions[0] ?? []) {
      if ((BOOSTS as string[]).includes(name)) needed.add(name as MoveBoost);
    }
  }
  return BOOSTS.filter((b) => needed.has(b));
}

/** The leg being edited in the route box, as a stageable leg (null = nothing to stage yet). */
export function draftAsLeg(
  draft: MoveDraft,
  id: string,
  ionStormToken?: boolean,
): StagedLeg | null {
  const route = draft.route;
  if (!route?.route) return null;
  if (legShipCount(draft.picks) + legCargoCount(draft.picks) === 0) return null;
  return {
    id,
    from: draft.from,
    faction: draft.faction,
    via: draft.via,
    picks: draft.picks,
    route,
    ionStormToken: route.ionStormChoice ? ionStormToken : undefined,
  };
}

/** Units of this pick key already staged in OTHER legs (the same ships cannot fly twice). */
export function stagedElsewhere(
  plan: StagedLeg[],
  exceptId: string | undefined,
  target: Pick<DraftPick, "kind" | "position" | "zone" | "baseType">,
): number {
  const key = pickKey(target);
  return plan
    .filter((leg) => leg.id !== exceptId)
    .reduce((n, leg) => n + (leg.picks[key]?.count ?? 0), 0);
}

/** Bonuses needed by more than one leg: each extends only one ship per action. */
export function boostConflicts(legs: StagedLeg[]): { boost: MoveBoost; froms: string[] }[] {
  return BOOSTS.flatMap((boost) => {
    const froms = legs
      .filter((leg) => neededBoosts(leg.route, leg.picks).includes(boost))
      .map((leg) => leg.from);
    return froms.length > 1 ? [{ boost, froms }] : [];
  });
}

/** Request body of one leg; only the bonuses this leg needs are spent on it. */
export function legRequest(leg: StagedLeg): MoveLegRequest {
  const boosts = neededBoosts(leg.route, leg.picks);
  const picks = Object.values(leg.picks).filter((p) => p.count > 0);
  return {
    faction: leg.faction,
    fromPosition: leg.from,
    ships: picks
      .filter((p) => p.kind === "ship")
      .map((p) => ({ baseType: p.baseType, count: p.count })),
    cargo: picks
      .filter((p) => p.kind === "cargo")
      .map((p) => ({
        baseType: p.baseType,
        count: p.count,
        fromZone: p.zone,
        fromPosition: p.position,
      })),
    route: leg.route.route,
    ionStormToken: leg.route.ionStormChoice ? (leg.ionStormToken ?? null) : null,
    gravityDrive: boosts.includes("gravity_drive"),
    tempesta: boosts.includes("tempesta"),
    imperator: boosts.includes("imperator"),
  };
}

/**
 * When a ship that "may move before or after your other ships" (Hil Colish, RULES.md 62.19)
 * flies: `auto` = after (every leg was previewed with that ship where it starts, so its delta
 * wormhole there stays usable - `⚠️ ASSUMPTION` in rules/R62.md).
 */
export type SeparateOrder = "auto" | "before" | "after";

/** A leg flying a ship that moves separately (by the route preview of the engine's hook). */
export function movesSeparately(leg: StagedLeg): boolean {
  return leg.route.ships.some(
    (ship) =>
      ship.movesSeparately === true &&
      Object.values(leg.picks).some(
        (p) => p.kind === "ship" && p.baseType === ship.baseType && p.count > 0,
      ),
  );
}

/** True when the order choice matters: a separately moving leg AND other legs in the plan. */
export function needsSeparateOrder(legs: StagedLeg[]): boolean {
  const separate = legs.filter(movesSeparately).length;
  return separate > 0 && separate < legs.length;
}

/**
 * Flights the plan is sent as, in order. "Before": the separate legs fly first as their own
 * request (the state is committed, the rest then fly with its delta in its NEW system);
 * "after" / auto: one request with the separate legs last.
 */
export function flightBatches(legs: StagedLeg[], order: SeparateOrder): StagedLeg[][] {
  if (!needsSeparateOrder(legs)) return legs.length > 0 ? [legs] : [];
  const separate = legs.filter(movesSeparately);
  const rest = legs.filter((leg) => !movesSeparately(leg));
  return order === "before" ? [separate, rest] : [[...rest, ...separate]];
}

export type IncomingFleet = {
  /** Ships flying in (asyncId -> count), fighters included. */
  ships: Record<string, number>;
  /** Cargo carried in (asyncId -> count). */
  cargo: Record<string, number>;
  nonFighterShips: number;
  fighters: number;
  groundForces: number;
  /** Capacity the incoming ships bring. */
  capacity: number;
};

/** Everything the plan brings into the active system (combined preview before flying). */
export function planIncoming(legs: StagedLeg[]): IncomingFleet {
  const incoming: IncomingFleet = {
    ships: {},
    cargo: {},
    nonFighterShips: 0,
    fighters: 0,
    groundForces: 0,
    capacity: 0,
  };
  for (const leg of legs) {
    for (const p of Object.values(leg.picks)) {
      if (p.count <= 0) continue;
      const asyncId = asyncOfBase(p.baseType);
      const bucket = p.kind === "ship" ? incoming.ships : incoming.cargo;
      bucket[asyncId] = (bucket[asyncId] ?? 0) + p.count;
      if (p.baseType === "fighter") incoming.fighters += p.count;
      else if (p.kind === "ship") incoming.nonFighterShips += p.count;
      else incoming.groundForces += p.count;
      if (p.kind === "ship") {
        const ship = leg.route.ships.find((s) => s.baseType === p.baseType);
        incoming.capacity += (ship?.capacity ?? 0) * p.count;
      }
    }
  }
  return incoming;
}

let legSeq = 0;
/** Fresh id for a staged leg. */
export function newLegId(): string {
  legSeq += 1;
  return `leg-${legSeq}`;
}
