import { getOwnedTwilightsFallUnitByAsyncId } from "@/entities/lookup/units";
import type { Unit } from "@/entities/data/types";

/** Printed unit stats plus whatever upgrades sit on top of the card (mech/Twilight's Fall techs). */
export function getUnitModifiers(unit: Unit, unitsOwned?: string[]) {
  const isMech = unit.baseType === "mech";
  const hasCabal = isMech && !!unitsOwned?.includes("tf-eidolonterminus");
  const hasNaaz = isMech && !!unitsOwned?.includes("tf-eidolonlandwaster");
  const hasNekro = isMech && !!unitsOwned?.includes("tf-valefarprime");
  const twilightsFall = getOwnedTwilightsFallUnitByAsyncId(unit.asyncId, unitsOwned);
  const upgradeFactions = Array.from(
    new Set([
      ...(hasCabal ? ["cabal"] : []),
      ...(hasNaaz ? ["naaz"] : []),
      ...(hasNekro ? ["nekro"] : []),
      ...(twilightsFall?.faction ? [twilightsFall.faction] : []),
    ]),
  );
  return {
    upgradeFactions,
    bonusCombatDice: hasNaaz ? 1 : undefined,
    combatValueModifier: hasCabal ? -1 : undefined,
    costModifier: hasNekro ? -1 : undefined,
  };
}

export const DEFAULT_UNIT_CAPS: Record<string, number> = {
  carrier: 4,
  mech: 4,
  flagship: 1,
  spacedock: 3,
  dreadnought: 5,
  destroyer: 8,
  cruiser: 8,
  pds: 6,
  warsun: 2,
  infantry: 12,
  fighter: 10,
};
