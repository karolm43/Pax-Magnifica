import type { GameData } from "@/entities/game/types";
import type { Point } from "@/entities/data/types";
import { getGenericUnitDataByAsyncId } from "@/entities/lookup/units";
import { getPlanetPositionsBySystemId } from "@/entities/lookup/planets";
import { EFFECT_DURATION_MS, type FlightEffectKind } from "@/entities/replay/flightPath";
import { tileCenter } from "@/entities/replay/liveMovement";
import type {
  LiveCannon,
  MapCombatLaser,
  MapFlightEffect,
} from "@/entities/replay/types";
import { allUnitStacks, stackHolder } from "@/entities/replay/unitState";

/**
 * Space Cannon Offense volley (Activity `spacecannon.fire`): every roll group fires bolts from
 * its shooter (a PDS planet, or a unit in space) at the target's ships in the active system.
 * Dice that hit strike a ship and flash; misses streak wide of the fleet. Pure planning: the
 * physical dice roll on the dice stage first, so the bolts wait for them to land.
 */

/** The physical dice are in the air and settle before the first bolt leaves. */
export const CANNON_DICE_LEAD_MS = 2600;
const BOLT_STAGGER_MS = 240;
const BOLT_DURATION_MS = 520;
/** Longest volley drawn: more dice than this are summarised by their hits only. */
const MAX_BOLTS_PER_GROUP = 6;
const MAX_BOLTS = 16;
/** A missed bolt sails this far (px) to the side of its target. */
const MISS_OFFSET_PX = 46;

export type CannonVolleyPlan = {
  lasers: MapCombatLaser[];
  effects: MapFlightEffect[];
  endMs: number;
};

/** Where a shooter stands: its planet, a unit in space, or the middle of its system. */
function shooterPoint(
  data: GameData,
  faction: string,
  position: string,
  zone: string,
): Point | undefined {
  const tile = data.tiles[position];
  if (!tile) return undefined;
  if (zone !== "space") {
    const local = getPlanetPositionsBySystemId(tile.systemId)[zone];
    if (local) return { x: tile.properties.x + local.x, y: tile.properties.y + local.y };
  } else {
    const stack = allUnitStacks(data).find(
      (located) =>
        located.position === position &&
        located.stack.faction === faction &&
        stackHolder(located.stack) === "space",
    );
    if (stack) return { x: stack.worldX, y: stack.worldY };
  }
  return tileCenter(data, position);
}

/** The target's ships in the active system (fallback: the middle of the system). */
function targetPoints(data: GameData, faction: string, position: string): Point[] {
  const ships = allUnitStacks(data)
    .filter(
      (located) =>
        located.position === position &&
        located.stack.faction === faction &&
        stackHolder(located.stack) === "space" &&
        getGenericUnitDataByAsyncId(located.stack.entityId)?.isShip === true,
    )
    .map((located) => ({ x: located.worldX, y: located.worldY }));
  if (ships.length > 0) return ships;
  const center = tileCenter(data, position);
  return center ? [center] : [];
}

export function buildCannonVolley(data: GameData, volley: LiveCannon): CannonVolleyPlan {
  const lasers: MapCombatLaser[] = [];
  const effects: MapFlightEffect[] = [];
  const targets = targetPoints(data, volley.targetFaction, volley.active);
  const effect = (kind: FlightEffectKind, point: Point, delayMs: number) =>
    effects.push({
      kind,
      x: point.x,
      y: point.y,
      delayMs: Math.round(delayMs),
      durationMs: EFFECT_DURATION_MS[kind],
    });
  let bolt = 0;
  if (targets.length > 0) {
    for (const [group, shot] of volley.shots.entries()) {
      const from = shooterPoint(data, volley.faction, shot.position, shot.zone);
      if (!from) continue;
      // Every group fires its dice; the hits come first so a hit is never dropped from the cap.
      const dice = Math.min(MAX_BOLTS_PER_GROUP, Math.max(shot.dice, shot.hits, 1));
      for (let die = 0; die < dice && bolt < MAX_BOLTS; die += 1, bolt += 1) {
        const hit = die < shot.hits;
        const aim = targets[(group + die) % targets.length];
        // A miss sails past the fleet, off to one side of the ship it was aimed at.
        const side = die % 2 === 0 ? 1 : -1;
        const length = Math.hypot(aim.x - from.x, aim.y - from.y) || 1;
        const to = hit
          ? aim
          : {
              x: aim.x - ((aim.y - from.y) / length) * MISS_OFFSET_PX * side,
              y: aim.y + ((aim.x - from.x) / length) * MISS_OFFSET_PX * side,
            };
        const delayMs = CANNON_DICE_LEAD_MS + bolt * BOLT_STAGGER_MS;
        lasers.push({
          fromX: from.x,
          fromY: from.y,
          toX: to.x,
          toY: to.y,
          delayMs,
          durationMs: BOLT_DURATION_MS,
          color: "cannon",
        });
        effect("cannonFlash", from, delayMs);
        // Only a hit strikes: its flash lands as the bolt arrives.
        if (hit) effect("cannonImpact", aim, delayMs + BOLT_DURATION_MS * 0.8);
      }
    }
  }
  const endMs = Math.max(
    0,
    ...lasers.map((laser) => laser.delayMs + laser.durationMs),
    ...effects.map((e) => e.delayMs + e.durationMs),
  );
  return { lasers, effects, endMs };
}
