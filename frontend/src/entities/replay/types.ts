import type { MapStatePreview } from "@/entities/game/types";
import type { EntityStack } from "@/entities/positioning";
import type { ControlTokenDisplayMode } from "@/entities/game/controlTokenDisplay";
import type { FlightEffect, FlightLeg } from "@/entities/replay/flightPath";

import type { StateCounts } from "@/entities/data/types";

export type { StateCounts };

export type DelayedDamage = { damageAtMs: number; states: StateCounts };

export type MapUnitTransition = {
  kind: "moved" | "removed" | "retreated" | "settled" | "added";
  stack: EntityStack;
  toX: number;
  toY: number;
  locationKey: string;
  delayMs?: number;
  layoutUnitStates?: StateCounts;
  layoutStateOffsets?: StateCounts;
  appearAtMs?: number;
  holdFromMs?: number;
  damageAtMs?: number;
  delayedDamageStates?: StateCounts;
  startRotationDeg?: number;
  parkRotationDeg?: number;
  holdRotationDeg?: number;
  hideAfterMs?: number;
  badgeCountChange?: boolean;
  residualAsset?: boolean;
  sourceHold?: boolean;
  continuation?: {
    toX: number;
    toY: number;
    delayMs: number;
    startRotationDeg?: number;
    parkRotationDeg?: number;
  };
  /**
   * Multi-hop route (live moves): waypoints after the start; the last leg ends at
   * `toX`/`toY`. Absent = the legacy single arc from the stack to `toX`/`toY`.
   */
  flightPath?: FlightLeg[];
  /**
   * Cargo (fighters / ground forces) packed into a carrier: shrinks into it at
   * `board`, rides hidden for `rideMs`, unpacks from the carrier's landing point
   * `land` to `toX`/`toY`. World coordinates; times from `delayMs`.
   */
  cargoRide?: CargoRide;
};

export type CargoRide = {
  boardX: number;
  boardY: number;
  landX: number;
  landY: number;
  packMs: number;
  rideMs: number;
  unpackMs: number;
};

/** A wormhole swirl or anomaly pulse drawn on the board during a flight. */
export type MapFlightEffect = Omit<FlightEffect, "atMs"> & { delayMs: number };

/**
 * A confirmed fleet move announced by the Activity feed (`move_route` fact): ordered route,
 * how each hop was crossed, anomalies on the way and the moving faction.
 */
export type LiveFleetMove = {
  kind: "move";
  faction: string;
  route: string[];
  /** One per hop: `lane` or the link that jumped it (`wormhole` / `portal` / `jump`). */
  hops: string[];
  anomalies: Record<string, string[]>;
};

/** Ground forces committed from space to planets (Activity `invasion.commit`). */
export type LiveLanding = {
  kind: "landing";
  faction: string;
  planets: string[];
};

/** A live board action replayed on every client. */
export type LiveMove = LiveFleetMove | LiveLanding;

export type MapCombatLaser = {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  delayMs: number;
  durationMs: number;
  color: "attacker" | "defender";
};

export type MapCommandTokenPlacement = {
  kind: "activation" | "added" | "removed";
  position: string;
  faction: string;
  index: number;
  x: number;
  y: number;
  delayMs: number;
  durationMs: number;
};

export type MapControlTokenTransition = {
  kind: "added" | "removed";
  position: string;
  planet: string;
  faction: string;
  x: number;
  y: number;
  delayMs: number;
  durationMs: number;
};

export type MapReplayPlan = {
  transitions: MapUnitTransition[];
  lasers: MapCombatLaser[];
  commandTokens: MapCommandTokenPlacement[];
  controlTokens: MapControlTokenTransition[];
  flightEffects: MapFlightEffect[];
  arrivalLocations: Set<string>;
  delayedDamage: Map<string, DelayedDamage>;
  baseUnitStates: Map<string, StateCounts>;
  finalRevealLocations: Set<string>;
  tacticalTargetPosition?: string;
  focusPosition?: string;
  showTacticalActivation: boolean;
  changedPositions: Set<string>;
  durationMs: number;
};

export type LocatedStack = {
  position: string;
  stack: EntityStack;
  worldX: number;
  worldY: number;
};

export type UnitLocation = {
  position: string;
  holder: string;
  faction: string;
  unitId: string;
};

/** The replay-relevant parts of a map preview, plus display options. */
export type AuthoritativeTransitionOptions = Pick<
  MapStatePreview,
  | "movementState"
  | "retreats"
  | "combats"
  | "activeFaction"
  | "tacticalPosition"
> & {
  controlTokenDisplayMode?: ControlTokenDisplayMode;
  changedPositions?: Set<string>;
  /** Live move from the Activity feed; replaces `movementState` for planning. */
  liveMove?: LiveMove;
};

export type PlannedMovement = {
  transition: MapUnitTransition;
  source: UnitLocation;
  sourceKey: string;
  destinationKey: string;
  target: UnitLocation;
  finalDestination?: LocatedStack;
  arrival: LocatedStack;
  staged: boolean;
};

export type ReplayInventory = {
  expectedTotals: Map<string, number>;
  finalTotals: Map<string, number>;
  locations: Map<string, UnitLocation>;
};

/** A movement with factions resolved: compact AsyncTI4 movement state or a live move. */
export type ResolvedMovement = {
  targetPosition: string;
  targetHolder: string;
  sources: {
    position: string;
    holder: string;
    units: {
      faction: string;
      unitId: string;
      states: StateCounts;
      /** Destination holder for this unit (landings spread over planets). */
      toHolder?: string;
    }[];
  }[];
};
