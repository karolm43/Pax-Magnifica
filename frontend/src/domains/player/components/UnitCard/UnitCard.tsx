import { useDisclosure } from "@/hooks/useDisclosure";
import styles from "./UnitCard.module.css";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { Unit } from "@/shared/ui/Unit";
import { BaseCard } from "./BaseCard";
import { DenseUnitCell } from "./DenseUnitCell";
import { getColorAlias } from "@/entities/lookup/colors";
import { getUnitData } from "@/entities/lookup/units";
import { useGameContext } from "@/state/useGameContext";
import { UnitDetails } from "./UnitDetails";
import { DEFAULT_UNIT_CAPS, getUnitModifiers } from "./unitModifiers";

type Props = {
  unitId: string;
  color?: string;
  deployedCount: number;
  unitCap?: number;
  condensed?: boolean;
  showUpgradeState?: boolean;
};

export function UnitCard({
  unitId,
  color,
  deployedCount,
  unitCap: unitCapProp,
  condensed,
  showUpgradeState = true,
}: Props) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const unitData = getUnitData(unitId);
  const colorAlias = getColorAlias(color);
  const gameData = useGameContext();

  if (!unitData) return null;

  const playerData = color
    ? gameData?.playerData?.find((p) => p.color === color)
    : undefined;
  const { upgradeFactions: allUpgradeFactions } = getUnitModifiers(
    unitData,
    playerData?.unitsOwned,
  );
  const unitIsUpgraded =
    unitData.upgradesFromUnitId !== undefined || unitData.baseType === "warsun";
  const isUpgraded =
    showUpgradeState && (unitIsUpgraded || allUpgradeFactions.length > 0);
  const upgradeFactions =
    showUpgradeState && allUpgradeFactions.length > 0
      ? allUpgradeFactions
      : undefined;
  const isFaction = unitData.faction !== undefined;
  const defaultCap = DEFAULT_UNIT_CAPS[unitData.baseType];
  const unitCap = unitCapProp ?? defaultCap;
  const reinforcements = unitCap - deployedCount;

  return (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>
        {condensed ? (
          <DenseUnitCell
            image={
              <Unit
                unitType={unitData.asyncId}
                colorAlias={colorAlias}
                faction={unitData.faction}
                className={styles.denseUnitImage}
                scaleSprite
                showFactionTokens={false}
              />
            }
            reinforcements={reinforcements}
            totalCapacity={unitCap}
            upgraded={isUpgraded}
            faction={isFaction ? unitData.faction : undefined}
            upgradeFactions={upgradeFactions}
            onClick={toggle}
          />
        ) : (
          <div style={{ minWidth: "44px" }}>
            <BaseCard
              onClick={toggle}
              isUpgraded={isUpgraded}
              isFaction={isFaction}
              faction={unitData.faction}
              reinforcements={reinforcements}
              totalCapacity={unitCap}
              upgradeFactions={upgradeFactions}
            >
              <Unit
                unitType={unitData.asyncId}
                colorAlias={colorAlias}
                faction={unitData.faction}
                className={styles.unitImage}
                scaleSprite
                showFactionTokens={false}
              />
            </BaseCard>
          </div>
        )}
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown className={styles.popoverDropdown}>
        <UnitDetails unitId={unitId} color={color} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
