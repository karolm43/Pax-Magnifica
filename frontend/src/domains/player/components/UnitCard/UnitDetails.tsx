import { UnitDetailsCard } from "@/domains/cards/components/UnitDetailsCard";
import { getUnitData, isNekroFlagship } from "@/entities/lookup/units";
import { useGameContext } from "@/state/useGameContext";
import { getUnitModifiers } from "./unitModifiers";

/** The full unit card as seen by its owner (modifiers, inherited abilities) - popover body. */
export function UnitDetails({ unitId, color }: { unitId: string; color?: string }) {
  const gameData = useGameContext();
  const unitData = getUnitData(unitId);
  if (!unitData) return null;
  const owner = color ? gameData?.playerData?.find((p) => p.color === color) : undefined;
  const { bonusCombatDice, combatValueModifier, costModifier } = getUnitModifiers(
    unitData,
    owner?.unitsOwned,
  );
  return (
    <UnitDetailsCard
      unitId={unitId}
      color={color}
      bonusCombatDice={bonusCombatDice}
      combatValueModifier={combatValueModifier}
      costModifier={costModifier}
      playerUnitsOwned={unitId === "pinktf_flagship" ? owner?.unitsOwned : undefined}
      valefarZTargets={isNekroFlagship(unitId) ? owner?.valefarZTargets : undefined}
      allPlayerData={isNekroFlagship(unitId) ? gameData?.playerData : undefined}
    />
  );
}
