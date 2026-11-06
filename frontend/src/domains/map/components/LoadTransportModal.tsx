import { useEffect, useMemo, useState } from "react";
import { ActionIcon, Button, Group, Stack, Text } from "@/ds";
import { IconMinus, IconPlus, IconPackage } from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { useAppStore } from "@/state/appStore";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor } from "@/api/useBoardEditor";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { lookupUnit } from "@/entities/lookup/units";
import { Unit } from "@/shared/ui/Unit";
import { baseTypeOf, CARGO_ASYNC } from "./UnitStack/cargo";
import styles from "./MoveUnitsModal.module.css";

/**
 * Okno ZAŁADUNKU transportu (RULES.md 32.3) — „zapakuj statkowi rzeczy".
 *
 * Otwierane dla wybranego statku-nosiciela w systemie źródłowym. Pokazuje jego
 * POJEMNOŚĆ i dostępny ładunek (myśliwce / siły naziemne) z przestrzeni tego
 * systemu. Gracz dokłada ładunek do limitu (z pomocą „Fill" / „Clear"), po czym
 * jednym walidowanym ``/tactical/move`` rusza nosiciela + ładunek do aktywnego
 * systemu. Zasięg i capacity egzekwuje backend (422 z powodem).
 */
export function LoadTransportModal() {
  const target = useAppStore((s) => s.loadTransport);
  const close = useAppStore((s) => s.closeLoadTransport);
  const gameData = useGameData();
  const { moveShips } = useBoardEditor();
  const [picked, setPicked] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setPicked({});
  }, [target]);

  const player = gameData?.playerData?.find((p) => p.faction === target?.faction);
  const colorAlias = getColorAlias(player?.color);

  // Pojemność jednego nosiciela (z wariantu gracza) — ile ładunku zmieści.
  const shipUnit = target
    ? lookupUnit(target.shipAsyncId, target.faction, player)
    : null;
  const shipCapacity = shipUnit?.capacityValue ?? 0;

  // Dostępny ładunek w systemie źródłowym: myśliwce/siły naziemne z PRZESTRZENI
  // ORAZ siły naziemne z PLANET (statek może je zabrać — RULES.md 32.3 T3). Każda
  // pozycja niesie strefę źródłową (``fromZone``: "space" albo id planety).
  const cargoStacks = useMemo(() => {
    if (!target) return [] as { asyncId: string; zone: string; label: string; count: number }[];
    const tile = gameData?.tiles?.[target.fromPosition];
    const out: { asyncId: string; zone: string; label: string; count: number }[] = [];
    for (const e of tile?.unitsByFaction?.[target.faction] ?? []) {
      if (e.entityType === "unit" && e.count > 0 && CARGO_ASYNC.has(e.entityId)) {
        out.push({ asyncId: e.entityId, zone: "space", label: "space", count: e.count });
      }
    }
    // Planety tego systemu — tylko siły naziemne (myśliwiec nie stoi na planecie).
    for (const [planetId, planet] of Object.entries(tile?.planets ?? {})) {
      for (const e of planet.unitsByFaction?.[target.faction] ?? []) {
        if (
          e.entityType === "unit" &&
          e.count > 0 &&
          CARGO_ASYNC.has(e.entityId) &&
          e.entityId !== "ff"
        ) {
          out.push({ asyncId: e.entityId, zone: planetId, label: planetId, count: e.count });
        }
      }
    }
    return out;
  }, [target, gameData?.tiles]);

  if (!target) return null;

  // Klucz wyboru = „asyncId@strefa" (ten sam typ z przestrzeni i z planety to różne pozycje).
  const keyOf = (asyncId: string, zone: string) => `${asyncId}@${zone}`;
  const loaded = Object.values(picked).reduce((a, b) => a + b, 0);
  const free = Math.max(shipCapacity - loaded, 0);

  const pick = (k: string, max: number, delta: number) => {
    setPicked((prev) => {
      const current = prev[k] ?? 0;
      // Nie pozwól przekroczyć capacity (suma) ani dostępnej liczby (max).
      const wouldBe = current + delta;
      const capped =
        delta > 0 ? Math.min(wouldBe, current + free, max) : Math.max(wouldBe, 0);
      return { ...prev, [k]: capped };
    });
  };

  const fill = () => {
    let remaining = shipCapacity;
    const next: Record<string, number> = {};
    for (const s of cargoStacks) {
      const take = Math.min(s.count, remaining);
      if (take > 0) next[keyOf(s.asyncId, s.zone)] = take;
      remaining -= take;
      if (remaining <= 0) break;
    }
    setPicked(next);
  };

  const confirm = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const cargo = cargoStacks
        .filter((s) => (picked[keyOf(s.asyncId, s.zone)] ?? 0) > 0)
        .map((s) => ({
          baseType: baseTypeOf(s.asyncId),
          count: picked[keyOf(s.asyncId, s.zone)],
          fromZone: s.zone,
        }));
      await moveShips({
        fromPosition: target.fromPosition,
        faction: target.faction,
        baseType: baseTypeOf(target.shipAsyncId),
        count: 1,
        cargo,
      });
      close();
    } finally {
      setBusy(false);
    }
  };

  const fromName =
    getTileById(gameData?.tiles?.[target.fromPosition]?.systemId ?? "")?.name ??
    target.fromPosition;

  return (
    <AppModal
      opened={!!target}
      onClose={close}
      title={`Load transport: ${target.fromPosition} ${fromName}`}
      size={460}
    >
      <Stack gap="md">
        {/* Nosiciel + jego pojemność. */}
        <Group gap="sm" align="center" wrap="nowrap">
          <div className={styles.unitIcon}>
            <Unit
              unitType={target.shipAsyncId}
              colorAlias={colorAlias}
              faction={target.faction}
              scaleSprite
            />
          </div>
          <Text size="sm" fw={600}>
            {target.shipAsyncId.toUpperCase()}
          </Text>
          <Text size="xs" c="dimmed" title="Cargo loaded / ship capacity">
            <IconPackage size={12} style={{ verticalAlign: -2 }} /> {loaded}/
            {shipCapacity}
            {free > 0 ? ` · ${free} free` : " · full"}
          </Text>
        </Group>

        {cargoStacks.length === 0 ? (
          <Text size="sm" c="dimmed">
            No fighters or ground forces in this system's space to load.
          </Text>
        ) : (
          <Stack gap={6}>
            {cargoStacks.map((s) => {
              const k = keyOf(s.asyncId, s.zone);
              const sel = picked[k] ?? 0;
              return (
                <Group key={k} gap="sm" justify="space-between" wrap="nowrap">
                  <Group gap="xs" wrap="nowrap">
                    <div className={styles.unitIcon}>
                      <Unit
                        unitType={s.asyncId}
                        colorAlias={colorAlias}
                        faction={target.faction}
                        scaleSprite
                      />
                    </div>
                    <Text size="sm">
                      <b>{sel}</b>/{s.count} {s.asyncId.toUpperCase()}
                    </Text>
                    <Text size="xs" c="dimmed" title="Pickup zone">
                      from {s.label}
                    </Text>
                  </Group>
                  <Group gap={4} wrap="nowrap">
                    <ActionIcon
                      size="sm"
                      variant="light"
                      disabled={busy || sel <= 0}
                      onClick={() => pick(k, s.count, -1)}
                      aria-label={`Unload ${s.asyncId}`}
                    >
                      <IconMinus size={13} />
                    </ActionIcon>
                    <ActionIcon
                      size="sm"
                      variant="light"
                      disabled={busy || sel >= s.count || free <= 0}
                      onClick={() => pick(k, s.count, +1)}
                      aria-label={`Load ${s.asyncId}`}
                    >
                      <IconPlus size={13} />
                    </ActionIcon>
                  </Group>
                </Group>
              );
            })}
          </Stack>
        )}

        <Group gap="xs">
          <Button
            size="xs"
            variant="default"
            disabled={busy || cargoStacks.length === 0}
            onClick={fill}
          >
            Fill to capacity
          </Button>
          <Button
            size="xs"
            variant="default"
            disabled={busy || loaded === 0}
            onClick={() => setPicked({})}
          >
            Clear
          </Button>
        </Group>

        <Group justify="flex-end" gap="xs">
          <Button variant="subtle" onClick={close} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={() => void confirm()} loading={busy}>
            Move ship + {loaded} cargo
          </Button>
        </Group>
      </Stack>
    </AppModal>
  );
}
