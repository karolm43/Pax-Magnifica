import { useMemo, useState } from "react";
import {
  ActionIcon,
  Button,
  Group,
  Select,
  Stack,
  Text,
} from "@/ds";
import { IconArrowRight } from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { getPlanetsByTileId } from "@/entities/lookup/planets";
import { Unit } from "@/shared/ui/Unit";
import { useBoardEditor } from "@/api/useBoardEditor";
import type { Tile } from "@/entities/game/types";
import type { EntityData } from "@/entities/data/types";
import styles from "./MoveUnitsModal.module.css";

/** Jedna pozycja do przeniesienia: frakcja + strefa źródłowa + jednostka + ile. */
type Movable = {
  faction: string;
  zone: string;
  zoneLabel: string;
  asyncId: string;
  count: number;
};

/** Zbiera wszystkie jednostki z systemu (Orbita + planety) jako płaską listę. */
function collectMovables(tile: Tile): Movable[] {
  const out: Movable[] = [];
  const push = (zone: string, zoneLabel: string, byFaction: Record<string, EntityData[]>) => {
    for (const [faction, entities] of Object.entries(byFaction)) {
      for (const e of entities) {
        if (e.entityType === "unit" && e.count > 0) {
          out.push({ faction, zone, zoneLabel, asyncId: e.entityId, count: e.count });
        }
      }
    }
  };
  push("space", "Space", tile.unitsByFaction);
  for (const [planetId, planet] of Object.entries(tile.planets)) {
    push(planetId, planetId, planet.unitsByFaction);
  }
  return out;
}

/** Strefy docelowe systemu: Orbita + jego planety. */
function destZones(tile: Tile): { value: string; label: string }[] {
  const planetIds = (getPlanetsByTileId(tile.systemId) ?? [])
    .map((p) => p.id)
    .filter((id) => tile.planets[id] !== undefined);
  return [
    { value: "space", label: "Space" },
    ...planetIds.map((id) => ({ value: id, label: id })),
  ];
}

/**
 * Menu „co przenieść" (God-Mode). Otwiera się po zaznaczeniu dwóch systemów w
 * trybie przenoszenia: pokazuje jednostki systemu źródłowego, pozwala wybrać
 * strefę docelową i przenieść jednostki (po 1 kliknięciem w strzałkę).
 */
export function MoveUnitsModal() {
  const movePair = useAppStore((s) => s.movePair);
  const clearMove = useAppStore((s) => s.clearMove);
  const gameData = useGameData();
  const { moveUnit } = useBoardEditor();
  const [toZone, setToZone] = useState<string>("space");
  const [busy, setBusy] = useState(false);

  const fromTile = movePair ? gameData?.tiles?.[movePair.from] : undefined;
  const toTile = movePair ? gameData?.tiles?.[movePair.to] : undefined;

  const movables = useMemo(
    () => (fromTile ? collectMovables(fromTile) : []),
    [fromTile],
  );
  const toZones = useMemo(() => (toTile ? destZones(toTile) : []), [toTile]);

  const fromName = fromTile
    ? getTileById(fromTile.systemId)?.name ?? fromTile.systemId
    : "";
  const toName = toTile
    ? getTileById(toTile.systemId)?.name ?? toTile.systemId
    : "";

  const move = async (m: Movable, count: number) => {
    if (!movePair || busy) return;
    setBusy(true);
    try {
      await moveUnit({
        fromPosition: movePair.from,
        fromZone: m.zone,
        toPosition: movePair.to,
        toZone,
        faction: m.faction,
        asyncId: m.asyncId,
        count,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppModal
      opened={!!movePair}
      onClose={clearMove}
      title={
        movePair
          ? `Move: ${movePair.from} ${fromName} → ${movePair.to} ${toName}`
          : "Move"
      }
      size={520}
    >
      <Stack gap="md">
        <Group gap="xs" align="center">
          <Text size="sm" c="dimmed">
            Destination zone
          </Text>
          <Select
            size="xs"
            data={toZones}
            value={toZone}
            onChange={(v) => setToZone(v ?? "space")}
          />
        </Group>

        {movables.length === 0 && (
          <Text size="sm" c="dimmed">
            The source system has no units to move.
          </Text>
        )}

        <Stack gap={6}>
          {movables.map((m, i) => {
            const player = gameData?.playerData?.find(
              (p) => p.faction === m.faction,
            );
            const colorAlias = getColorAlias(player?.color);
            return (
              <Group
                key={`${m.faction}-${m.zone}-${m.asyncId}-${i}`}
                gap="sm"
                justify="space-between"
                wrap="nowrap"
              >
                <Group gap="xs" wrap="nowrap">
                  <div className={styles.unitIcon}>
                    <Unit
                      unitType={m.asyncId}
                      colorAlias={colorAlias}
                      faction={m.faction}
                      scaleSprite
                    />
                  </div>
                  <Text size="sm">
                    <b>{m.count}×</b> {m.asyncId.toUpperCase()}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {(player?.flexibleDisplayName || m.faction).toUpperCase()} ·{" "}
                    {m.zoneLabel}
                  </Text>
                </Group>
                <Group gap={4} wrap="nowrap">
                  <ActionIcon
                    size="sm"
                    variant="light"
                    disabled={busy}
                    onClick={() => void move(m, 1)}
                    title="Move 1"
                  >
                    <IconArrowRight size={13} />
                  </ActionIcon>
                  <Button
                    size="xs"
                    variant="default"
                    disabled={busy}
                    onClick={() => void move(m, m.count)}
                    title="Move all"
                  >
                    All
                  </Button>
                </Group>
              </Group>
            );
          })}
        </Stack>

        <Group justify="flex-end">
          <Button variant="default" size="xs" onClick={clearMove}>
            Close
          </Button>
        </Group>
      </Stack>
    </AppModal>
  );
}
