import { ActionIcon, Group, Stack, Text } from "@/ds";
import { IconMinus } from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { Unit } from "@/shared/ui/Unit";
import {
  useBoardEditor,
  useCombatHelp,
  type CombatSideHelp,
} from "@/api/useBoardEditor";
import styles from "./MoveUnitsModal.module.css";

/**
 * Okno walki (asystent, E3). NIE rozstrzyga walki — gracze rzucają kośćmi i
 * ustalają trafienia fizycznie, a tu tylko odejmują zniszczone jednostki
 * (przycisk „−1" = God-Mode edit-units delta -1). Obok każdej jednostki pomoce
 * liczbowe: liczba kości, trafia na X+, oczekiwane trafienia; na dole suma strony.
 */
function CombatSide({
  side,
  position,
  planet,
}: {
  side: CombatSideHelp;
  position: string;
  planet: string | null;
}) {
  const gameData = useGameData();
  const { editUnit } = useBoardEditor();
  const player = gameData?.playerData?.find((p) => p.faction === side.faction);
  const colorAlias = getColorAlias(player?.color);
  const zone = planet ?? "space";

  const removeOne = (asyncId: string) =>
    void editUnit({
      position,
      zone,
      faction: side.faction,
      asyncId,
      delta: -1,
    });

  return (
    <Stack gap={6} className={styles.combatSide}>
      <Group gap="xs" justify="space-between">
        <Text size="sm" fw={600}>
          {(player?.flexibleDisplayName || side.faction).toUpperCase()}
        </Text>
        <Text size="xs" c="dimmed" title="Suma kości · oczekiwane trafienia">
          {side.totalDice} kości · ~{side.expectedHits} traf.
        </Text>
      </Group>
      {side.units.map((u) => (
        <Group key={u.asyncId} gap="sm" justify="space-between" wrap="nowrap">
          <Group gap="xs" wrap="nowrap">
            <div className={styles.unitIcon}>
              <Unit
                unitType={u.asyncId}
                colorAlias={colorAlias}
                faction={side.faction}
                scaleSprite
              />
            </div>
            <Text size="sm">
              <b>{u.count}×</b> {u.name}
            </Text>
            <Text size="xs" c="dimmed" title="Trafia na X+ · liczba kości na sztukę">
              {u.combatHitsOn}+ ×{u.combatDieCount} · ~{u.expectedHits}
            </Text>
          </Group>
          <ActionIcon
            size="sm"
            variant="light"
            color="red"
            onClick={() => removeOne(u.asyncId)}
            title="Usuń 1 (zniszczona)"
          >
            <IconMinus size={13} />
          </ActionIcon>
        </Group>
      ))}
    </Stack>
  );
}

export function CombatModal() {
  const combatTarget = useAppStore((s) => s.combatTarget);
  const closeCombat = useAppStore((s) => s.closeCombat);
  const gameData = useGameData();
  const { data } = useCombatHelp(
    combatTarget?.position ?? null,
    combatTarget?.planet ?? null,
  );

  const position = combatTarget?.position ?? null;
  const planet = combatTarget?.planet ?? null;
  const tile = position ? gameData?.tiles?.[position] : undefined;
  const sysName = tile
    ? getTileById(tile.systemId)?.name ?? tile.systemId
    : position;
  const where = planet ? `${sysName} · ${planet}` : sysName;

  return (
    <AppModal
      opened={!!combatTarget}
      onClose={closeCombat}
      title={`Walka ${planet ? "naziemna" : "kosmiczna"}: ${where ?? ""}`}
      size={620}
    >
      <Stack gap="md">
        <Text size="xs" c="dimmed">
          Pomoc liczbowa — rzuty i trafienia ustalacie przy stole. Odejmuj
          zniszczone jednostki przyciskiem „−1".
        </Text>
        {!data || data.sides.length === 0 ? (
          <Text size="sm" c="dimmed">
            Brak walki w tym miejscu (potrzebne siły co najmniej dwóch graczy).
          </Text>
        ) : (
          <Group align="flex-start" grow gap="lg">
            {data.sides.map((side) => (
              <CombatSide
                key={side.faction}
                side={side}
                position={data.position}
                planet={data.planet}
              />
            ))}
          </Group>
        )}
      </Stack>
    </AppModal>
  );
}
