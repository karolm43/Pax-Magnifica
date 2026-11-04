import { useEffect, useState } from "react";
import { Button, Group, NumberInput, Stack, Text } from "@/ds";
import { AppModal } from "@/shared/ui/AppModal";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { Unit } from "@/shared/ui/Unit";
import { useBoardEditor } from "@/api/useBoardEditor";
import styles from "./MoveUnitsModal.module.css";

/**
 * Pytanie „ile przenieść" po upuszczeniu STOSU jednostek (drag-and-drop). Otwiera
 * się ze stanu ``unitDrop`` (ustawianego przez useUnitDrag, gdy przeciągnięto stos
 * >1 sztuki na inną strefę). Pokazuje przeciąganą jednostkę, skąd→dokąd, i pozwala
 * wybrać liczbę: szybkie przyciski (1 / połowa / wszystkie) + pole liczbowe, po czym
 * jedno kliknięcie „Przenieś". Pojedyncze sztuki przenosi już sam gest (bez okna).
 */
export function MoveQuantityModal() {
  const drop = useAppStore((s) => s.unitDrop);
  const clearUnitDrop = useAppStore((s) => s.clearUnitDrop);
  const gameData = useGameData();
  const { moveUnit } = useBoardEditor();
  const [count, setCount] = useState(1);
  const [busy, setBusy] = useState(false);

  // Domyślnie przenosimy całość (najczęstszy przypadek przy DnD stosu).
  useEffect(() => {
    if (drop) setCount(drop.available);
  }, [drop]);

  if (!drop) return null;

  const player = gameData?.playerData?.find((p) => p.faction === drop.faction);
  const colorAlias = getColorAlias(player?.color);
  const fromName =
    getTileById(gameData?.tiles?.[drop.fromPosition]?.systemId ?? "")?.name ??
    drop.fromPosition;
  const toName =
    getTileById(gameData?.tiles?.[drop.toPosition]?.systemId ?? "")?.name ??
    drop.toPosition;
  const fromZoneLabel = drop.fromZone === "space" ? "Space" : drop.fromZone;

  const clamp = (n: number) => Math.max(1, Math.min(drop.available, n));

  const confirm = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await moveUnit({
        fromPosition: drop.fromPosition,
        fromZone: drop.fromZone,
        toPosition: drop.toPosition,
        toZone: drop.toZone,
        faction: drop.faction,
        asyncId: drop.asyncId,
        count: clamp(count),
      });
      clearUnitDrop();
    } finally {
      setBusy(false);
    }
  };

  const half = Math.max(1, Math.floor(drop.available / 2));

  return (
    <AppModal
      opened={!!drop}
      onClose={clearUnitDrop}
      title={`Move: ${drop.fromPosition} ${fromName} → ${drop.toPosition} ${toName}`}
      size={420}
    >
      <Stack gap="md">
        <Group gap="sm" align="center" wrap="nowrap">
          <div className={styles.unitIcon}>
            <Unit
              unitType={drop.asyncId}
              colorAlias={colorAlias}
              faction={drop.faction}
              scaleSprite
            />
          </div>
          <Text size="sm">
            <b>{drop.asyncId.toUpperCase()}</b> ·{" "}
            {(player?.flexibleDisplayName || drop.faction).toUpperCase()}
          </Text>
          <Text size="xs" c="dimmed">
            {fromZoneLabel} → {drop.toLabel}
          </Text>
        </Group>

        <Group gap="xs" align="center">
          <Text size="sm" c="dimmed" style={{ minWidth: 72 }}>
            How many
          </Text>
          <NumberInput
            size="sm"
            value={count}
            min={1}
            max={drop.available}
            onChange={(v) => setCount(clamp(Number(v) || 1))}
            style={{ width: 90 }}
          />
          <Text size="xs" c="dimmed">
            of {drop.available}
          </Text>
        </Group>

        <Group gap="xs">
          <Button
            size="xs"
            variant="default"
            onClick={() => setCount(1)}
            disabled={busy}
          >
            1
          </Button>
          <Button
            size="xs"
            variant="default"
            onClick={() => setCount(half)}
            disabled={busy || drop.available < 2}
          >
            Half ({half})
          </Button>
          <Button
            size="xs"
            variant="default"
            onClick={() => setCount(drop.available)}
            disabled={busy}
          >
            All ({drop.available})
          </Button>
        </Group>

        <Group justify="flex-end" gap="xs">
          <Button variant="subtle" onClick={clearUnitDrop} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={() => void confirm()} loading={busy}>
            Move {clamp(count)}
          </Button>
        </Group>
      </Stack>
    </AppModal>
  );
}
