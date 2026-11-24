import { useState } from "react";
import { Box, Button, Text, UnstyledButton } from "@/ds";
import { Surface } from "@/shared/ui/Surface";
import { units } from "@/entities/data/units";
import { CapturedUnitsData } from "@/entities/data/types";
import styles from "./Nombox.module.css";
import { getColorAlias } from "@/entities/lookup/colors";
import { useFactionColors } from "@/hooks/useFactionColors";
import { useGameData } from "@/state/useGameContext";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import { Unit } from "@/shared/ui/Unit";
import { FactionIcon } from "@/shared/ui/FactionIcon";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { useBoardEditor } from "@/api/useBoardEditor";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { unitName } from "@/domains/game-shell/components/TurnControls/transactionItems";

type Props = {
  capturedUnits?: CapturedUnitsData;
  /** Faction whose sheet this is (the capturer) - own captured units can be returned. */
  ownerFaction?: string;
};

/** Fighter/infantry entries are supply tokens (they belong to no one) - never "own" units. */
const TOKEN_TYPES = new Set(["fighter", "infantry"]);

/**
 * R_capture notes/5 (RULES.md 61.5): a player who captured their OWN units may return them to
 * reinforcements at any time - click the unit on their own sheet.
 */
function ReturnOwnUnit({ faction, unitType, children }: {
  faction: string;
  unitType: string;
  children: React.ReactNode;
}) {
  const [opened, setOpened] = useState(false);
  const { captureReturnOwn } = useBoardEditor();
  const name = unitName(unitType);
  return (
    <SmoothPopover opened={opened} onChange={setOpened} position="top">
      <SmoothPopover.Target>
        <UnstyledButton
          className={styles.ownUnitButton}
          aria-label={`Return captured ${name} to reinforcements`}
          onClick={() => setOpened((o) => !o)}
        >
          {children}
        </UnstyledButton>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown>
        <Surface className={styles.returnCard}>
          <Text size="xs">Your own captured {name}. You may return it to your reinforcements at any time.</Text>
          <Button
            size="xs"
            onClick={() => {
              setOpened(false);
              void captureReturnOwn(faction, unitType, 1);
            }}
          >
            Return 1 to reinforcements
          </Button>
        </Surface>
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}

/** Parses a captured-unit entry like "dread,3" or "carrier,4". */
const parseUnitString = (unitString: string) => {
  const [unitType, countStr] = unitString.split(",");
  const count = parseInt(countStr, 10);
  const unit = units.find((u) => u.baseType === unitType);

  return {
    unitType,
    count,
    asyncId: unit?.asyncId || unitType.substring(0, 2),
  };
};

export function Nombox({ capturedUnits, ownerFaction }: Props) {
  const factionColorMap = useFactionColors();
  const gameData = useGameData();
  const desk = useDeskPlayer();
  const mine = !!ownerFaction && desk?.faction === ownerFaction;
  // Pełna nazwa frakcji z danych gracza (nigdy surowe id - RULES.md 61.5).
  const nameOf = (faction: string) => {
    const player = gameData?.playerData?.find((p) => p.faction === faction);
    return player ? getPlayerFactionDisplayName(player) : faction;
  };

  if (!capturedUnits || Object.keys(capturedUnits).length === 0) {
    return null;
  }

  return (
    <Surface className={styles.compactNombox}>
      <Text className={styles.compactTitle}>CAPTURED</Text>
      <Box className={styles.compactGrid}>
        {Object.entries(capturedUnits).map(([factionName, unitStrings]) => {
          const colorAlias = getColorAlias(factionColorMap?.[factionName]?.color);
          return (
            <Box key={factionName} className={styles.compactFaction}>
              <Box className={styles.compactFactionHeader}>
                <FactionIcon
                  faction={factionName}
                  className={styles.compactFactionIcon}
                />
                <Text className={styles.compactFactionName}>{nameOf(factionName)}</Text>
              </Box>
              <Box className={styles.compactUnitsRow}>
                {unitStrings.map((unitString, index) => {
                  const { unitType, count, asyncId } = parseUnitString(unitString);
                  const group = (
                    <Box className={styles.compactUnitGroup}>
                      <Box className={styles.compactUnitContainer}>
                        <Unit
                          unitType={asyncId}
                          colorAlias={colorAlias}
                          faction={factionName}
                          className={styles.compactUnitImage}
                          scaleSprite
                        />
                      </Box>
                      <Text className={styles.compactCountBadge}>×{count}</Text>
                    </Box>
                  );
                  const own = mine && factionName === ownerFaction && !TOKEN_TYPES.has(unitType);
                  return own ? (
                    <ReturnOwnUnit key={index} faction={factionName} unitType={unitType}>
                      {group}
                    </ReturnOwnUnit>
                  ) : (
                    <Box key={index}>{group}</Box>
                  );
                })}
              </Box>
            </Box>
          );
        })}
      </Box>
    </Surface>
  );
}
