import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Group, Stack, Text } from "@/ds";
import {
  IconAlertTriangle,
  IconCheck,
  IconMinus,
  IconPlus,
  IconRotate,
  IconWand,
} from "@tabler/icons-react";
import { AppModal } from "@/shared/ui/AppModal";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { useBoardEditor, useFleetPool } from "@/api/useBoardEditor";
import { CircularFactionIcon } from "@/shared/ui/CircularFactionIcon";
import { Unit } from "@/shared/ui/Unit";
import { getColorAlias } from "@/entities/lookup/colors";
import { getTileById } from "@/entities/lookup/systems";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import styles from "./CapacityModal.module.css";

/**
 * Okno FLEET POOL (RULES.md 42) - „masz w systemie więcej statków niż żetonów w puli floty".
 *
 * Reguła pozwala ruszyć / wyprodukować / postawić statki ponad pulę, ale nadwyżkę trzeba zaraz
 * zwrócić do rezerwy. Silnik otwiera okno ``FLEET_POOL`` przy próbie przejścia do kolejnego
 * kroku akcji (po ruchu, produkcji, walce). Modal adresuje BIEŻĄCEGO respondenta i jest
 * nieodrzucalny. Gracz wybiera, które statki odchodzą - dokładnie tyle, ile trzeba; myśliwce
 * i siły naziemne nie liczą się do puli.
 */
export function FleetPoolModal() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const { fleetPoolResolve } = useBoardEditor();
  const window = gameState?.pendingWindow ?? null;
  const pending =
    !!window && window.windowType === "FLEET_POOL" && !window.isComplete;
  const { data: view } = useFleetPool(pending);
  const [remove, setRemove] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);

  // Nowy respondent / nowe okno -> zacznij od podpowiedzi silnika.
  const viewKey = view?.active
    ? `${view.playerId}@${view.position}:${view.total}`
    : null;
  useEffect(() => {
    // Podpowiedź ładujemy tylko przy zmianie okna/respondenta (viewKey).
    if (viewKey && view) setRemove({ ...view.suggestion });
  }, [viewKey]);

  if (!pending || !view?.active) return null;

  const player = gameData?.playerData?.find((p) => p.faction === view.player);
  const name = player
    ? getPlayerFactionDisplayName(player)
    : (view.player ?? "");
  const colorAlias = getColorAlias(player?.color);
  const tile = view.position ? gameData?.tiles?.[view.position] : undefined;
  const systemName =
    (tile ? getTileById(tile.systemId)?.name : undefined) ??
    view.position ??
    "";

  const removedTotal = Object.values(remove).reduce((a, b) => a + b, 0);
  const status =
    removedTotal < view.excess
      ? "over"
      : removedTotal > view.excess
        ? "tooMany"
        : "exact";

  const step = (bt: string, max: number, delta: number) =>
    setRemove((prev) => ({
      ...prev,
      [bt]: Math.max(0, Math.min(max, (prev[bt] ?? 0) + delta)),
    }));

  const confirm = () => {
    if (busy || status !== "exact" || !view.player) return;
    setBusy(true);
    void fleetPoolResolve(view.player, remove).finally(() => setBusy(false));
  };

  return (
    <AppModal
      opened
      // Wymuszone: nadwyżkę statków trzeba zwrócić (R_fleet_pool) - modal znika po zamknięciu okna.
      onClose={() => {}}
      withCloseButton={false}
      closeOnClickOutside={false}
      closeOnEscape={false}
      title="Fleet pool exceeded"
      size={520}
    >
      <Stack gap="md">
        <Group gap="sm" wrap="nowrap">
          {player?.faction ? (
            <CircularFactionIcon faction={player.faction} size={34} />
          ) : null}
          <Stack gap={2} style={{ minWidth: 0 }}>
            <Text size="xs" c="dimmed">
              Your call · {systemName}
              {view.position && systemName !== view.position
                ? ` (${view.position})`
                : ""}
            </Text>
            <Text fw={700}>{name}</Text>
          </Stack>
        </Group>

        <Text size="sm">
          Your fleet pool allows <b>{view.pool}</b> non-fighter ship
          {view.pool === 1 ? "" : "s"} in a system, but you have{" "}
          <b>{view.total}</b> here. Choose <b>{view.excess}</b> to return to
          your reinforcements. Fighters, ground forces and units on planets
          don't count.
        </Text>

        <Stack gap={8}>
          {view.ships.map((c) => {
            const n = remove[c.baseType] ?? 0;
            return (
              <div key={c.baseType} className={styles.row}>
                <div className={styles.sprite}>
                  <Unit
                    unitType={c.asyncId}
                    colorAlias={colorAlias}
                    faction={player?.faction}
                    scaleSprite
                  />
                </div>
                <div className={styles.rowInfo}>
                  <b>{c.name}</b>
                  <span className={styles.tokens} aria-hidden="true">
                    {Array.from({ length: c.count }, (_, i) => (
                      <span
                        key={i}
                        className={styles.token}
                        data-removed={i >= c.count - n || undefined}
                      />
                    ))}
                  </span>
                  <small>
                    {c.count} in system · keep {c.count - n}
                    {n > 0 ? ` · remove ${n}` : ""}
                  </small>
                </div>
                <div className={styles.stepper}>
                  <button
                    type="button"
                    disabled={busy || n <= 0}
                    onClick={() => step(c.baseType, c.count, -1)}
                    aria-label={`Keep one more ${c.name}`}
                  >
                    <IconMinus size={14} />
                  </button>
                  <span
                    className={styles.stepValue}
                    data-active={n > 0 || undefined}
                  >
                    {n}
                  </span>
                  <button
                    type="button"
                    disabled={busy || n >= c.count}
                    onClick={() => step(c.baseType, c.count, +1)}
                    aria-label={`Remove one ${c.name}`}
                  >
                    <IconPlus size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </Stack>

        <div className={styles.status} data-status={status} role="status">
          {status === "over" && (
            <>
              <IconAlertTriangle size={15} aria-hidden="true" /> Remove{" "}
              {view.excess - removedTotal} more ship
              {view.excess - removedTotal === 1 ? "" : "s"}.
            </>
          )}
          {status === "tooMany" && (
            <>
              <IconAlertTriangle size={15} aria-hidden="true" /> You're removing
              more than needed - keep some back.
            </>
          )}
          {status === "exact" && (
            <>
              <IconCheck size={15} aria-hidden="true" /> Fits the pool.{" "}
              {removedTotal} ship{removedTotal === 1 ? "" : "s"} return to
              reinforcements.
            </>
          )}
        </div>

        <Group justify="space-between" gap="xs">
          <Group gap="xs">
            <Button
              size="xs"
              variant="default"
              leftSection={<IconWand size={14} />}
              disabled={busy}
              onClick={() => setRemove({ ...view.suggestion })}
            >
              Auto
            </Button>
            <Button
              size="xs"
              variant="default"
              leftSection={<IconRotate size={14} />}
              disabled={busy || removedTotal === 0}
              onClick={() => setRemove({})}
            >
              Reset
            </Button>
          </Group>
          <Button
            leftSection={<IconCheck size={16} />}
            disabled={status !== "exact"}
            loading={busy}
            onClick={confirm}
          >
            Remove {removedTotal} ship{removedTotal === 1 ? "" : "s"}
          </Button>
        </Group>

        {view.remaining > 1 && (
          <Text size="xs" c="dimmed">
            {view.remaining - 1} more player
            {view.remaining - 1 === 1 ? "" : "s"} must check the fleet pool
            after you.
          </Text>
        )}
      </Stack>
    </AppModal>
  );
}

export default FleetPoolModal;
