import { useMemo, useState } from "react";
import { ActionIcon, Group, SegmentedControl, Stack, Text } from "@/ds";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import { useGameData } from "@/state/useGameContext";
import { getColorAlias } from "@/entities/lookup/colors";
import { getPlanetsByTileId } from "@/entities/lookup/planets";
import { Unit } from "@/shared/ui/Unit";
import { useBoardEditor } from "@/api/useBoardEditor";
import type { Tile } from "@/entities/game/types";
import type { EntityData } from "@/entities/data/types";
import styles from "./SystemEditor.module.css";

/** Typy jednostek edytowalne w God-Mode, w kolejności jak w panelu gracza. */
const EDITABLE_UNITS: { asyncId: string; label: string }[] = [
  { asyncId: "ws", label: "War Sun" },
  { asyncId: "fs", label: "Flagship" },
  { asyncId: "dn", label: "Dread" },
  { asyncId: "cv", label: "Carrier" },
  { asyncId: "ca", label: "Cruiser" },
  { asyncId: "dd", label: "Destroyer" },
  { asyncId: "ff", label: "Fighter" },
  { asyncId: "mf", label: "Mech" },
  { asyncId: "gf", label: "Infantry" },
  { asyncId: "sd", label: "Space Dock" },
  { asyncId: "pd", label: "PDS" },
];

/** Liczy jednostki danego asyncId dla frakcji w danej liście encji. */
function countOf(entities: EntityData[] | undefined, asyncId: string): number {
  if (!entities) return 0;
  return entities
    .filter((e) => e.entityType === "unit" && e.entityId === asyncId)
    .reduce((sum, e) => sum + e.count, 0);
}

type Props = {
  tile: Tile;
};

/**
 * Edytor planszy (God-Mode) wewnątrz dossier systemu. Pozwala dodawać/usuwać
 * jednostki dowolnego gracza w przestrzeni lub na dowolnej planecie systemu —
 * bez sprawdzania zasad. Zmiany idą do backendu i odświeżają stan.
 */
export function SystemEditor({ tile }: Props) {
  const gameData = useGameData();
  const { editUnit } = useBoardEditor();
  const [busy, setBusy] = useState(false);

  const players = gameData?.playerData ?? [];
  const planetIds = useMemo(
    () =>
      (getPlanetsByTileId(tile.systemId) ?? [])
        .map((p) => p.id)
        .filter((id) => tile.planets[id] !== undefined),
    [tile.systemId, tile.planets],
  );

  // Strefy: Orbita (space) + każda planeta systemu.
  const zones = useMemo(
    () => [
      { value: "space", label: "Orbita" },
      ...planetIds.map((id) => ({ value: id, label: id })),
    ],
    [planetIds],
  );

  const [faction, setFaction] = useState<string>(
    players[0]?.faction ?? "",
  );
  const [zone, setZone] = useState<string>("space");

  if (players.length === 0) {
    return (
      <div className={styles.editor}>
        <Text size="sm" c="dimmed">
          Brak graczy — najpierw utwórz grę.
        </Text>
      </div>
    );
  }

  const activePlayer = players.find((p) => p.faction === faction) ?? players[0];
  const colorAlias = getColorAlias(activePlayer.color);

  // Bieżące jednostki wybranej frakcji w wybranej strefie.
  const zoneEntities =
    zone === "space"
      ? tile.unitsByFaction[faction]
      : tile.planets[zone]?.unitsByFaction[faction];

  const apply = async (asyncId: string, delta: number) => {
    if (busy) return;
    setBusy(true);
    try {
      await editUnit({
        position: tile.position,
        zone,
        faction,
        asyncId,
        delta,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.editor}>
      <Stack gap="xs">
        <Group gap="xs" wrap="wrap">
          <Text size="xs" c="dimmed" className={styles.sectionLabel}>
            Gracz
          </Text>
          <SegmentedControl
            size="xs"
            value={faction}
            onChange={setFaction}
            data={players.map((p) => ({
              value: p.faction,
              label: (p.flexibleDisplayName || p.faction).toUpperCase(),
            }))}
          />
        </Group>

        <Group gap="xs" wrap="wrap">
          <Text size="xs" c="dimmed" className={styles.sectionLabel}>
            Strefa
          </Text>
          <SegmentedControl
            size="xs"
            value={zone}
            onChange={setZone}
            data={zones}
          />
        </Group>

        <div className={styles.unitGrid}>
          {EDITABLE_UNITS.map(({ asyncId, label }) => {
            const count = countOf(zoneEntities, asyncId);
            return (
              <div key={asyncId} className={styles.unitCell}>
                <div className={styles.unitIcon}>
                  <Unit
                    unitType={asyncId}
                    colorAlias={colorAlias}
                    faction={activePlayer.faction}
                    scaleSprite
                    className={styles.unitSprite}
                  />
                </div>
                <Text size="10px" c="dimmed" className={styles.unitLabel}>
                  {label}
                </Text>
                <Group gap={4} justify="center" wrap="nowrap">
                  <ActionIcon
                    size="sm"
                    variant="default"
                    disabled={busy || count === 0}
                    onClick={() => void apply(asyncId, -1)}
                    aria-label={`Usuń ${label}`}
                  >
                    <IconMinus size={12} />
                  </ActionIcon>
                  <Text size="sm" fw={600} className={styles.unitCount}>
                    {count}
                  </Text>
                  <ActionIcon
                    size="sm"
                    variant="default"
                    disabled={busy}
                    onClick={() => void apply(asyncId, +1)}
                    aria-label={`Dodaj ${label}`}
                  >
                    <IconPlus size={12} />
                  </ActionIcon>
                </Group>
              </div>
            );
          })}
        </div>
      </Stack>
    </div>
  );
}
